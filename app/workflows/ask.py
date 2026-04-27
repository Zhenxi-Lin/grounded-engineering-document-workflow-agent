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
COMMAND_RE = re.compile(r"^(?:\$|mkdir|cd |source |colcon |git |make |ros2 |python |export |cmake |sudo )", re.IGNORECASE)
NOISE_PATTERNS = (
    "info",
    "warning",
    "note",
    "further information",
    "source code available on github",
)
PROCEDURAL_TERMS = (
    "install",
    "setup",
    "set up",
    "create",
    "build",
    "run",
    "launch",
    "source",
    "configure",
    "clone",
    "download",
    "workspace",
    "colcon",
)
VALIDATION_TERMS = (
    "verify",
    "check",
    "confirm",
    "ensure",
    "successfully",
    "without error",
    "ros2doctor",
    "source local_setup",
    "run the example",
    "all checks passed",
)
LEADING_PROCEDURAL_PREFIX_RE = re.compile(
    r"^(?:first|next|then|finally|in this tutorial,\s*you|to run .*?,\s*you need to|you need to)\s+",
    re.IGNORECASE,
)
SPECIFIC_PROJECT_TERMS = (
    "isaac ros",
    "isaac",
    "moveit",
    "px4",
    "nitros",
    "cumotion",
    "offboard",
    "uorb",
    "qgroundcontrol",
)
PROJECT_SPECIFIC_PATH_MARKERS = (
    "isaac_ros-dev",
    "ws_moveit",
    "px4_",
    "release-4.",
    "workspaces/isaac",
)
GENERAL_PROCEDURAL_TERMS = (
    "create a workspace",
    "creating a workspace",
    "installation",
    "setup",
    "build",
    "workspace",
    "colcon",
    "source",
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
        generic_procedural = is_generic_procedural_query(normalized_query, route)
        raw_top_k = max(self.evidence_top_k * 2, 8) if is_likely_procedural_query(route) else self.evidence_top_k
        raw_results = self.retrieval_service.search(
            normalized_query,
            mode=self.retrieval_mode,
            top_k=raw_top_k,
        )
        results = select_workflow_results(
            raw_results,
            query=normalized_query,
            route=route,
            limit=self.evidence_top_k,
        )
        citations = build_citations(results, self.retrieval_mode)

        if not results:
            LOGGER.info("No retrieval results found for query: %s", normalized_query)
            return build_insufficient_answer(
                query=normalized_query,
                confidence=0.0,
                citations=[],
            )

        snippets = collect_evidence_snippets(results, route, generic_procedural=generic_procedural)
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
            route = infer_query_route(query)
            user_prompt = build_grounded_qa_user_prompt(
                query=query,
                evidence_results=results,
                generic_procedural=is_generic_procedural_query(query, route),
                preferred_sources=route.preferred_sources,
            )
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
    is_procedural = is_likely_procedural_query(route)
    if not has_sufficient_evidence(results, snippets, route):
        LOGGER.info("Evidence judged insufficient for query: %s", query)
        return build_insufficient_answer(
            query=query,
            confidence=estimate_confidence(results, snippets, sufficient=False),
            citations=citations,
        )

    answer_payload = compose_answer_payload(snippets, route)
    if not answer_payload["answer"]:
        LOGGER.info("Could not compose answer text from evidence for query: %s", query)
        return build_insufficient_answer(
            query=query,
            confidence=estimate_confidence(results, snippets, sufficient=False),
            citations=citations,
        )
    if is_procedural and len(answer_payload["key_steps"]) < 3:
        LOGGER.info("Procedural evidence did not support 3 actionable steps for query: %s", query)
        return build_insufficient_answer(
            query=query,
            confidence=estimate_confidence(results, snippets, sufficient=False),
            citations=citations,
        )

    return GroundedAnswer(
        query=query,
        answer=answer_payload["answer"],
        status="grounded_answer",
        confidence=estimate_confidence(results, snippets, sufficient=True),
        key_steps=answer_payload["key_steps"],
        validation_check=answer_payload["validation_check"],
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
        key_steps=[],
        validation_check="",
        citations=citations,
    )


def validate_and_build_llm_answer(
    *,
    query: str,
    payload: LLMGroundedAnswerPayload,
    citations: list[Citation],
) -> GroundedAnswer:
    route = infer_query_route(query)
    if payload.status == "grounded_answer" and not payload.answer.strip():
        raise ValueError("LLM grounded_answer payload must include a non-empty answer")

    used_citations = map_used_citation_ids(payload.used_citation_ids, citations)
    if payload.status == "grounded_answer" and not used_citations:
        raise ValueError("LLM grounded answer must reference at least one valid citation id")
    if is_likely_procedural_query(route) and payload.status == "grounded_answer":
        if not (3 <= len(payload.key_steps) <= 5):
            raise ValueError("LLM procedural grounded answer must include 3 to 5 key_steps")
    if payload.status == "grounded_answer" and is_generic_procedural_query(query, route):
        if contains_project_specific_content(payload.answer):
            raise ValueError("LLM generic procedural answer overfit to project-specific content")
        if any(contains_project_specific_content(step) for step in payload.key_steps):
            raise ValueError("LLM generic procedural key_steps contain project-specific content")
        if payload.validation_check and contains_project_specific_content(payload.validation_check):
            raise ValueError("LLM generic procedural validation_check contains project-specific content")
        if route.preferred_sources:
            preferred_source = route.preferred_sources[0]
            if not any(citation.source == preferred_source for citation in used_citations):
                raise ValueError("LLM generic procedural answer must cite the preferred general source")

    answer_text = payload.answer.strip() or INSUFFICIENT_EVIDENCE_ANSWER
    key_steps = payload.key_steps[:5]
    validation_check = payload.validation_check.strip()
    if payload.status == "insufficient_evidence":
        answer_text = INSUFFICIENT_EVIDENCE_ANSWER
        key_steps = []
        validation_check = ""

    return GroundedAnswer(
        query=query,
        answer=answer_text,
        status=payload.status,
        confidence=payload.confidence,
        key_steps=key_steps,
        validation_check=validation_check,
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


def select_workflow_results(
    results: list[dict[str, Any]],
    *,
    query: str,
    route: QueryRoute,
    limit: int,
) -> list[dict[str, Any]]:
    if not results:
        return []
    if not is_likely_procedural_query(route):
        return results[:limit]

    generic_procedural = is_generic_procedural_query(query, route)
    scored: list[dict[str, Any]] = []
    for result in results:
        entry = dict(result)
        score = extract_display_score(result, "hybrid")
        source = str(result.get("source", ""))
        doc_type = str(result.get("doc_type", ""))
        combined_text = " ".join(
            [
                str(result.get("title", "")),
                str(result.get("topic", "")),
                " ".join(str(item) for item in result.get("section_path", [])),
                format_result_preview(str(result.get("text", "")), max_chars=220),
            ]
        ).lower()

        if source in route.preferred_sources:
            score += 0.16
        if doc_type in route.preferred_doc_types:
            score += 0.08
        if generic_procedural:
            if route.preferred_sources and source == route.preferred_sources[0]:
                score += 0.22
            if any(term in combined_text for term in GENERAL_PROCEDURAL_TERMS):
                score += 0.08
            if contains_project_specific_content(combined_text):
                score -= 0.24
        entry["_ask_workflow_score"] = score
        scored.append(entry)

    scored.sort(key=lambda item: item["_ask_workflow_score"], reverse=True)
    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for result in scored:
        url = str(result.get("url", ""))
        if url in seen_urls and len(selected) >= 2:
            continue
        seen_urls.add(url)
        selected.append(result)
        if len(selected) >= limit:
            break
    return selected


def collect_evidence_snippets(
    results: list[dict[str, Any]],
    route: QueryRoute,
    *,
    generic_procedural: bool,
) -> list[EvidenceSnippet]:
    candidates: list[EvidenceSnippet] = []
    query_keywords = route.topic_keywords
    is_procedural = is_likely_procedural_query(route)

    for chunk_rank, result in enumerate(results, start=1):
        base_score = extract_display_score(result, "hybrid")
        text = str(result.get("text", ""))
        source = str(result.get("source", ""))
        doc_type = str(result.get("doc_type", ""))
        source_bonus = get_source_bonus(source, route)
        doc_type_bonus = get_doc_type_bonus(doc_type, route)
        for unit in split_into_candidate_units(text, route):
            if generic_procedural and contains_project_specific_content(unit):
                continue
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
    return dedupe_snippets(
        prioritized,
        limit=5 if is_procedural else 4,
        max_per_chunk=3 if is_procedural else 2,
    )


def split_into_candidate_units(text: str, route: QueryRoute) -> list[str]:
    units: list[str] = []
    procedural = is_likely_procedural_query(route)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        raw_pieces = [line] if COMMAND_RE.match(line) else SENTENCE_SPLIT_RE.split(line)
        for raw_piece in raw_pieces:
            piece = clean_candidate_text(raw_piece)
            if not piece:
                continue
            if is_noise_piece(piece, procedural=procedural):
                continue
            units.append(piece)
    return units


def clean_candidate_text(text: str) -> str:
    piece = HEADING_RE.sub("", text.strip())
    piece = re.sub(r"\s+", " ", piece)
    return piece.strip(" -")


def is_noise_piece(text: str, *, procedural: bool) -> bool:
    lowered = text.lower()
    if len(lowered) < (12 if procedural else 35):
        return True
    if all(char in "#*-_ " for char in lowered):
        return True
    return any(pattern in lowered for pattern in NOISE_PATTERNS)


def dedupe_snippets(
    snippets: list[EvidenceSnippet],
    *,
    limit: int,
    max_per_chunk: int,
) -> list[EvidenceSnippet]:
    selected: list[EvidenceSnippet] = []
    seen_texts: set[str] = set()
    chunk_counts: dict[str, int] = {}

    for snippet in snippets:
        normalized = normalize_text(snippet.text)
        if normalized in seen_texts:
            continue
        if chunk_counts.get(snippet.chunk_id, 0) >= max_per_chunk:
            continue
        seen_texts.add(normalized)
        chunk_counts[snippet.chunk_id] = chunk_counts.get(snippet.chunk_id, 0) + 1
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


def compose_answer_payload(
    snippets: list[EvidenceSnippet],
    route: QueryRoute,
) -> dict[str, Any]:
    if not snippets:
        return {"answer": "", "key_steps": [], "validation_check": ""}

    if is_likely_procedural_query(route):
        key_steps = extract_key_steps(snippets)
        validation_check = extract_validation_check(snippets)
        answer_text = compose_procedural_answer(key_steps)
        return {
            "answer": answer_text,
            "key_steps": key_steps,
            "validation_check": validation_check,
        }

    answer_snippets = select_answer_snippets(snippets, route)
    selected_texts = [trim_sentence(snippet.text) for snippet in answer_snippets]
    selected_texts = [text for text in selected_texts if text]
    if not selected_texts:
        return {"answer": "", "key_steps": [], "validation_check": ""}

    if route.intent == "troubleshooting":
        checks = [convert_to_check_text(text) for text in selected_texts[:3]]
        answer_text = "Based on the retrieved documentation, the most relevant checks are: " + " ".join(
            f"{index}. {item}" for index, item in enumerate(checks, start=1)
        )
        return {"answer": answer_text, "key_steps": [], "validation_check": ""}

    first = selected_texts[0]
    remainder = " ".join(selected_texts[1:3])
    if remainder:
        answer_text = f"Based on the retrieved documentation, {first} {remainder}"
    else:
        answer_text = f"Based on the retrieved documentation, {first}"
    return {"answer": answer_text, "key_steps": [], "validation_check": ""}


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


def extract_key_steps(snippets: list[EvidenceSnippet]) -> list[str]:
    if not snippets:
        return []

    primary_chunk_id = snippets[0].chunk_id
    primary_source = snippets[0].source
    steps: list[str] = []
    seen: set[str] = set()
    preferred_order = (
        [snippet for snippet in snippets if snippet.chunk_id == primary_chunk_id]
        + [snippet for snippet in snippets if snippet.chunk_id != primary_chunk_id and snippet.source == primary_source]
        + [snippet for snippet in snippets if snippet.source != primary_source]
    )

    for snippet in preferred_order:
        candidate = normalize_step_text(snippet.text)
        for raw_candidate in iter_procedural_step_candidates(snippet, primary_source):
            candidate = normalize_step_text(raw_candidate)
            if not candidate:
                continue
            normalized = normalize_text(candidate)
            if normalized in seen:
                continue
            if not looks_like_procedural_step(candidate):
                continue
            if should_skip_procedural_step(candidate):
                continue
            seen.add(normalized)
            steps.append(candidate)
            if len(steps) >= 5:
                break
        if len(steps) >= 5:
            break

    return steps


def extract_validation_check(snippets: list[EvidenceSnippet]) -> str:
    for snippet in snippets:
        candidate = trim_sentence(snippet.text)
        lowered = candidate.lower()
        if any(term in lowered for term in VALIDATION_TERMS):
            return candidate
    return ""


def looks_like_procedural_step(text: str) -> bool:
    lowered = text.lower()
    if COMMAND_RE.match(text):
        return True
    if lowered.startswith(("source ", "create ", "build ", "install ", "run ", "launch ", "configure ", "clone ", "download ", "navigate ", "open ", "start ")):
        return True
    if "you need to" in lowered:
        return True
    if any(term in lowered for term in PROCEDURAL_TERMS):
        return True
    return False


def should_skip_procedural_step(text: str) -> bool:
    lowered = text.lower()
    generic_labels = {
        "installation",
        "getting started",
        "overview",
        "ubuntu (binary)",
    }
    skip_patterns = (
        "recommended",
        "which install should you choose",
        "general use",
        "differences between the options",
        "installed successfully",
    )
    if lowered in generic_labels:
        return True
    return any(pattern in lowered for pattern in skip_patterns)


def normalize_step_text(text: str) -> str:
    cleaned = trim_sentence(text)
    cleaned = LEADING_PROCEDURAL_PREFIX_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")
    if not cleaned:
        return ""
    cleaned = convert_leading_verb_to_imperative(cleaned)
    if COMMAND_RE.match(cleaned):
        return cleaned
    if cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned


def iter_procedural_step_candidates(
    snippet: EvidenceSnippet,
    primary_source: str,
) -> list[str]:
    candidates = [snippet.text]

    if snippet.source == primary_source:
        for section in reversed(snippet.section_path):
            section_text = str(section).strip()
            if not section_text:
                continue
            candidates.append(section_text)

    return candidates


def compose_procedural_answer(key_steps: list[str]) -> str:
    if not key_steps:
        return ""
    if len(key_steps) == 1:
        return f"Based on the retrieved documentation, the task starts by {lowercase_initial(key_steps[0])}."
    return (
        "Based on the retrieved documentation, the main flow is to "
        f"{lowercase_initial(key_steps[0])}, then {lowercase_initial(key_steps[1])}."
    )


def trim_sentence(text: str) -> str:
    cleaned = text.strip()
    return cleaned.rstrip(".")


def convert_to_step_text(text: str) -> str:
    return text


def convert_to_check_text(text: str) -> str:
    return text


def lowercase_initial(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if COMMAND_RE.match(stripped):
        return stripped
    return stripped[0].lower() + stripped[1:]


def convert_leading_verb_to_imperative(text: str) -> str:
    replacements = {
        "sourced ": "Source ",
        "created ": "Create ",
        "built ": "Build ",
        "cloned ": "Clone ",
        "installed ": "Install ",
        "configured ": "Configure ",
        "launched ": "Launch ",
        "downloaded ": "Download ",
        "navigated ": "Navigate ",
        "ran ": "Run ",
        "changed ": "Change ",
        "creating ": "Create ",
        "building ": "Build ",
    }
    lowered = text.lower()
    for prefix, replacement in replacements.items():
        if lowered.startswith(prefix):
            return replacement + text[len(prefix):]
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


def is_likely_procedural_query(route: QueryRoute) -> bool:
    return route.intent == "procedural"


def is_generic_procedural_query(query: str, route: QueryRoute) -> bool:
    if not is_likely_procedural_query(route):
        return False
    lowered = query.lower()
    return not any(term in lowered for term in SPECIFIC_PROJECT_TERMS)


def contains_project_specific_content(text: str) -> bool:
    lowered = text.lower()
    if any(marker in lowered for marker in PROJECT_SPECIFIC_PATH_MARKERS):
        return True
    return any(term in lowered for term in SPECIFIC_PROJECT_TERMS)


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
