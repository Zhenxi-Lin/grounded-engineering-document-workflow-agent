from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.llm_client import LLMClient
from app.models.answer_models import Citation, GroundedAnswer, LLMGroundedAnswerPayload
from app.prompts.grounded_qa import SYSTEM_PROMPT, build_grounded_qa_user_prompt
from app.retrieval.query_router import QueryRoute, infer_query_route
from app.retrieval.retrieval_service import RetrievalService, extract_display_score, format_result_preview


LOGGER = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE_ANSWER = "Available evidence was not sufficient to support a grounded answer."
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
HEADING_RE = re.compile(r"^#{1,6}\s*")
NOISE_PATTERNS = (
    "info",
    "warning",
    "note",
    "further information",
    "source code available on github",
)


@dataclass(frozen=True)
class EvidenceSnippet:
    chunk_id: str
    text: str
    score: float
    title: str
    source: str
    version: str
    section_path: list[str]
    url: str
    chunk_rank: int


class GroundedQAWorkflow:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        retrieval_mode: str = "hybrid",
        evidence_top_k: int = 4,
        llm_client: LLMClient | None = None,
        enable_llm_synthesis: bool = True,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.retrieval_mode = retrieval_mode
        self.evidence_top_k = evidence_top_k
        self.llm_client = llm_client
        self.enable_llm_synthesis = enable_llm_synthesis

    @classmethod
    def from_index_dir(
        cls,
        index_dir: Path,
        *,
        retrieval_mode: str = "hybrid",
        evidence_top_k: int = 4,
        llm_client: LLMClient | None = None,
        enable_llm_synthesis: bool = True,
    ) -> "GroundedQAWorkflow":
        return cls(
            retrieval_service=RetrievalService.from_index_dir(index_dir),
            retrieval_mode=retrieval_mode,
            evidence_top_k=evidence_top_k,
            llm_client=llm_client,
            enable_llm_synthesis=enable_llm_synthesis,
        )

    def answer(self, query: str) -> GroundedAnswer:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Query cannot be empty")

        route = infer_query_route(normalized_query)
        results = self.retrieval_service.search(
            normalized_query,
            mode=self.retrieval_mode,
            top_k=self.evidence_top_k,
        )
        citations = build_citations(results, self.retrieval_mode)

        if not results:
            LOGGER.info("No retrieval results found for query: %s", normalized_query)
            return build_insufficient_answer(
                query=normalized_query,
                confidence=0.0,
                citations=[],
            )

        snippets = collect_evidence_snippets(results, route)
        fallback_answer = build_extractive_answer(
            query=normalized_query,
            route=route,
            results=results,
            snippets=snippets,
            citations=citations,
        )
        if fallback_answer.status == "insufficient_evidence":
            return fallback_answer

        llm_answer = self._try_llm_synthesis(
            query=normalized_query,
            results=results,
            citations=citations,
        )
        if llm_answer is not None:
            return llm_answer

        LOGGER.info("Falling back to extractive grounded answer for query: %s", normalized_query)
        return fallback_answer

    def _try_llm_synthesis(
        self,
        *,
        query: str,
        results: list[dict[str, Any]],
        citations: list[Citation],
    ) -> GroundedAnswer | None:
        if not self.enable_llm_synthesis:
            LOGGER.info("LLM synthesis is disabled; using extractive fallback")
            return None
        if self.llm_client is None:
            LOGGER.info("No LLM client configured; using extractive fallback")
            return None

        try:
            user_prompt = build_grounded_qa_user_prompt(query=query, evidence_results=results)
            llm_payload = self.llm_client.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            parsed_payload = LLMGroundedAnswerPayload.from_dict(llm_payload)
            return validate_and_build_llm_answer(
                query=query,
                payload=parsed_payload,
                citations=citations,
            )
        except Exception as exc:
            LOGGER.warning("LLM synthesis failed validation or request handling: %s", exc)
            return None


def build_extractive_answer(
    *,
    query: str,
    route: QueryRoute,
    results: list[dict[str, Any]],
    snippets: list[EvidenceSnippet],
    citations: list[Citation],
) -> GroundedAnswer:
    if not has_sufficient_evidence(results, snippets, route):
        LOGGER.info("Evidence judged insufficient for query: %s", query)
        return build_insufficient_answer(
            query=query,
            confidence=estimate_confidence(results, snippets, sufficient=False),
            citations=citations,
        )

    answer_text = compose_answer(snippets, route)
    if not answer_text:
        LOGGER.info("Could not compose answer text from evidence for query: %s", query)
        return build_insufficient_answer(
            query=query,
            confidence=estimate_confidence(results, snippets, sufficient=False),
            citations=citations,
        )

    return GroundedAnswer(
        query=query,
        answer=answer_text,
        status="grounded_answer",
        confidence=estimate_confidence(results, snippets, sufficient=True),
        citations=citations,
    )


def build_insufficient_answer(
    *,
    query: str,
    confidence: float,
    citations: list[Citation],
) -> GroundedAnswer:
    return GroundedAnswer(
        query=query,
        answer=INSUFFICIENT_EVIDENCE_ANSWER,
        status="insufficient_evidence",
        confidence=confidence,
        citations=citations,
    )


def validate_and_build_llm_answer(
    *,
    query: str,
    payload: LLMGroundedAnswerPayload,
    citations: list[Citation],
) -> GroundedAnswer:
    if payload.status == "grounded_answer" and not payload.answer.strip():
        raise ValueError("LLM grounded_answer payload must include a non-empty answer")

    used_citations = map_used_citation_ids(payload.used_citation_ids, citations)
    if payload.status == "grounded_answer" and not used_citations:
        raise ValueError("LLM grounded answer must reference at least one valid citation id")

    answer_text = payload.answer.strip() or INSUFFICIENT_EVIDENCE_ANSWER
    if payload.status == "insufficient_evidence":
        answer_text = INSUFFICIENT_EVIDENCE_ANSWER

    return GroundedAnswer(
        query=query,
        answer=answer_text,
        status=payload.status,
        confidence=payload.confidence,
        citations=used_citations,
    )


def map_used_citation_ids(
    used_citation_ids: list[str],
    citations: list[Citation],
) -> list[Citation]:
    citation_by_id = {citation.chunk_id: citation for citation in citations}
    mapped: list[Citation] = []
    seen: set[str] = set()

    for citation_id in used_citation_ids:
        if citation_id not in citation_by_id:
            raise ValueError(f"Unknown citation id returned by LLM: {citation_id}")
        if citation_id in seen:
            continue
        seen.add(citation_id)
        mapped.append(citation_by_id[citation_id])

    return mapped


def build_citations(results: list[dict[str, Any]], retrieval_mode: str) -> list[Citation]:
    citations: list[Citation] = []
    for result in results:
        citations.append(
            Citation(
                chunk_id=str(result.get("chunk_id", "")),
                title=str(result.get("title", "")),
                source=str(result.get("source", "")),
                version=str(result.get("version", "")),
                section_path=[str(item) for item in result.get("section_path", [])],
                url=str(result.get("url", "")),
                score=round(extract_display_score(result, retrieval_mode), 4),
                snippet=format_result_preview(str(result.get("text", "")), max_chars=220),
            )
        )
    return citations


def collect_evidence_snippets(
    results: list[dict[str, Any]],
    route: QueryRoute,
) -> list[EvidenceSnippet]:
    candidates: list[EvidenceSnippet] = []
    query_keywords = route.topic_keywords

    for chunk_rank, result in enumerate(results, start=1):
        base_score = extract_display_score(result, "hybrid")
        text = str(result.get("text", ""))
        source = str(result.get("source", ""))
        doc_type = str(result.get("doc_type", ""))
        source_bonus = get_source_bonus(source, route)
        doc_type_bonus = get_doc_type_bonus(doc_type, route)
        for unit in split_into_candidate_units(text):
            overlap = count_overlap(query_keywords, unit)
            intent_bonus = score_intent_alignment(unit, route)
            if overlap == 0 and intent_bonus == 0.0:
                continue

            snippet_score = (
                base_score
                + source_bonus
                + doc_type_bonus
                + overlap * 0.08
                + intent_bonus
                - (chunk_rank - 1) * 0.01
            )
            candidates.append(
                EvidenceSnippet(
                    chunk_id=str(result.get("chunk_id", "")),
                    text=unit,
                    score=snippet_score,
                    title=str(result.get("title", "")),
                    source=source,
                    version=str(result.get("version", "")),
                    section_path=[str(item) for item in result.get("section_path", [])],
                    url=str(result.get("url", "")),
                    chunk_rank=chunk_rank,
                )
            )

    candidates.sort(key=lambda item: item.score, reverse=True)
    prioritized = prioritize_routed_snippets(candidates, route)
    return dedupe_snippets(prioritized, limit=4)


def split_into_candidate_units(text: str) -> list[str]:
    units: list[str] = []
    for raw_piece in SENTENCE_SPLIT_RE.split(text):
        piece = clean_candidate_text(raw_piece)
        if not piece:
            continue
        if is_noise_piece(piece):
            continue
        units.append(piece)
    return units


def clean_candidate_text(text: str) -> str:
    piece = HEADING_RE.sub("", text.strip())
    piece = re.sub(r"\s+", " ", piece)
    return piece.strip(" -")


def is_noise_piece(text: str) -> bool:
    lowered = text.lower()
    if len(lowered) < 35:
        return True
    if all(char in "#*-_ " for char in lowered):
        return True
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def dedupe_snippets(snippets: list[EvidenceSnippet], *, limit: int) -> list[EvidenceSnippet]:
    selected: list[EvidenceSnippet] = []
    seen_texts: set[str] = set()
    seen_chunk_ids: set[str] = set()

    for snippet in snippets:
        normalized = normalize_text(snippet.text)
        if normalized in seen_texts:
            continue
        if snippet.chunk_id in seen_chunk_ids and len(selected) >= 2:
            continue
        seen_texts.add(normalized)
        seen_chunk_ids.add(snippet.chunk_id)
        selected.append(snippet)
        if len(selected) >= limit:
            break

    return selected


def prioritize_routed_snippets(
    snippets: list[EvidenceSnippet],
    route: QueryRoute,
) -> list[EvidenceSnippet]:
    if not route.preferred_sources and not route.preferred_doc_types:
        return snippets

    preferred: list[EvidenceSnippet] = []
    fallback: list[EvidenceSnippet] = []
    for snippet in snippets:
        if snippet.source in route.preferred_sources:
            preferred.append(snippet)
        else:
            fallback.append(snippet)

    if len(preferred) >= 2:
        return preferred + fallback
    return snippets


def has_sufficient_evidence(
    results: list[dict[str, Any]],
    snippets: list[EvidenceSnippet],
    route: QueryRoute,
) -> bool:
    if not results or not snippets:
        return False

    top_score = extract_display_score(results[0], "hybrid")
    strong_snippets = [snippet for snippet in snippets if snippet.score >= top_score + 0.04]
    supporting_chunks = {snippet.chunk_id for snippet in snippets[:3]}

    if top_score >= 0.34 and len(strong_snippets) >= 1:
        return True
    if top_score >= 0.24 and len(snippets) >= 2 and len(supporting_chunks) >= 2:
        return True
    if route.intent == "procedural" and top_score >= 0.22 and len(supporting_chunks) >= 2:
        return True
    return False


def compose_answer(snippets: list[EvidenceSnippet], route: QueryRoute) -> str:
    if not snippets:
        return ""

    answer_snippets = select_answer_snippets(snippets, route)
    selected_texts = [trim_sentence(snippet.text) for snippet in answer_snippets]
    selected_texts = [text for text in selected_texts if text]
    if not selected_texts:
        return ""

    if route.intent == "procedural":
        steps = [convert_to_step_text(text) for text in selected_texts[:3]]
        return "Based on the retrieved documentation, the main procedure is: " + " ".join(
            f"{index}. {step}" for index, step in enumerate(steps, start=1)
        )

    if route.intent == "troubleshooting":
        checks = [convert_to_check_text(text) for text in selected_texts[:3]]
        return "Based on the retrieved documentation, the most relevant checks are: " + " ".join(
            f"{index}. {item}" for index, item in enumerate(checks, start=1)
        )

    first = selected_texts[0]
    remainder = " ".join(selected_texts[1:3])
    if remainder:
        return f"Based on the retrieved documentation, {first} {remainder}"
    return f"Based on the retrieved documentation, {first}"


def select_answer_snippets(
    snippets: list[EvidenceSnippet],
    route: QueryRoute,
) -> list[EvidenceSnippet]:
    if not snippets:
        return []

    primary = snippets[0]
    same_chunk = [snippet for snippet in snippets if snippet.chunk_id == primary.chunk_id]
    same_source = [
        snippet
        for snippet in snippets
        if snippet.chunk_id != primary.chunk_id and snippet.source == primary.source
    ]
    target_size = 2
    if route.intent == "procedural" and len(same_chunk) + len(same_source) >= 3:
        target_size = 3

    preferred_source = [
        snippet
        for snippet in snippets
        if snippet.chunk_id != primary.chunk_id
        and snippet.source in route.preferred_sources
        and snippet.source != primary.source
    ]
    others = [
        snippet
        for snippet in snippets
        if snippet.chunk_id != primary.chunk_id
        and snippet.source != primary.source
        and snippet.source not in route.preferred_sources
    ]

    ordered = same_chunk + same_source + preferred_source + others
    selected: list[EvidenceSnippet] = []
    seen_texts: set[str] = set()
    for snippet in ordered:
        normalized = normalize_text(snippet.text)
        if normalized in seen_texts:
            continue
        seen_texts.add(normalized)
        selected.append(snippet)
        if len(selected) >= target_size:
            break
    return selected


def trim_sentence(text: str) -> str:
    cleaned = text.strip()
    return cleaned.rstrip(".")


def convert_to_step_text(text: str) -> str:
    return text


def convert_to_check_text(text: str) -> str:
    return text


def estimate_confidence(
    results: list[dict[str, Any]],
    snippets: list[EvidenceSnippet],
    *,
    sufficient: bool,
) -> float:
    if not results:
        return 0.0

    top_score = extract_display_score(results[0], "hybrid")
    snippet_factor = min(len(snippets), 3) * 0.08
    score_factor = min(top_score * 1.25, 0.55)
    base = 0.18 if sufficient else 0.05
    confidence = base + score_factor + snippet_factor
    if not sufficient:
        confidence = min(confidence, 0.35)
    return max(0.0, min(confidence, 0.9))


def count_overlap(query_keywords: list[str], text: str) -> int:
    lowered = text.lower()
    return sum(1 for keyword in query_keywords if keyword in lowered)


def score_intent_alignment(text: str, route: QueryRoute) -> float:
    lowered = text.lower()
    if route.intent == "procedural":
        if contains_any(lowered, ["install", "build", "run", "launch", "source", "workspace", "colcon", "setup"]):
            return 0.08
    elif route.intent == "troubleshooting":
        if contains_any(lowered, ["error", "failsafe", "compatibility", "mismatch", "overflow", "check"]):
            return 0.08
    else:
        if contains_any(lowered, ["is", "refers to", "provides", "uses", "supports", "overview"]):
            return 0.06
    return 0.0


def get_source_bonus(source: str, route: QueryRoute) -> float:
    if source in route.preferred_sources:
        source_rank = route.preferred_sources.index(source)
        return max(0.12 - source_rank * 0.03, 0.04)
    return 0.0


def get_doc_type_bonus(doc_type: str, route: QueryRoute) -> float:
    if doc_type in route.preferred_doc_types:
        doc_type_rank = route.preferred_doc_types.index(doc_type)
        return max(0.08 - doc_type_rank * 0.02, 0.03)
    return 0.0


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def build_grounded_qa_workflow(
    *,
    index_dir: Path,
    retrieval_mode: str = "hybrid",
    evidence_top_k: int = 4,
    llm_client: LLMClient | None = None,
    enable_llm_synthesis: bool = True,
) -> GroundedQAWorkflow:
    return GroundedQAWorkflow.from_index_dir(
        index_dir,
        retrieval_mode=retrieval_mode,
        evidence_top_k=evidence_top_k,
        llm_client=llm_client,
        enable_llm_synthesis=enable_llm_synthesis,
    )
