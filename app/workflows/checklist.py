from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from app.llm_client import LLMClient
from app.models.answer_models import Citation
from app.models.checklist_models import GroundedChecklist, LLMGroundedChecklistPayload
from app.prompts.grounded_checklist import SYSTEM_PROMPT, build_grounded_checklist_user_prompt
from app.retrieval.query_router import QueryRoute, infer_query_route
from app.retrieval.retrieval_service import RetrievalService, extract_display_score, format_result_preview


LOGGER = logging.getLogger(__name__)

INSUFFICIENT_TITLE = "Checklist Evidence Insufficient"
INSUFFICIENT_SUMMARY = "Available evidence was not sufficient to support a grounded checklist."
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
HEADING_RE = re.compile(r"^#{1,6}\s*")
COMMAND_RE = re.compile(r"^(?:\$|mkdir|cd |source |colcon |git |make |ros2 |python |export )", re.IGNORECASE)
PROCEDURE_HINTS = (
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
    "initialize",
)
PREREQUISITE_HINTS = (
    "before",
    "prerequisite",
    "require",
    "required",
    "supported",
    "underlay",
    "environment",
    "workspace",
    "install",
)
WARNING_HINTS = (
    "warning",
    "caution",
    "fails",
    "failure",
    "error",
    "mismatch",
    "overflow",
    "interfer",
    "compatibility",
)
VALIDATION_HINTS = (
    "verify",
    "check",
    "confirm",
    "validate",
    "run the example",
    "ensure",
    "source local_setup",
)
NOISE_PATTERNS = (
    "see also",
    "additional resources",
    "further information",
    "next step",
    "source code available on github",
)
ACTION_PREFIXES = (
    "create",
    "build",
    "run",
    "install",
    "set up",
    "setup",
    "configure",
    "source",
    "launch",
    "clone",
    "download",
    "open",
    "start",
    "check",
    "verify",
    "confirm",
    "remove",
)
CHECKLIST_DOC_TYPE_PRIORITIES = {
    "installation": 0.18,
    "tutorial": 0.16,
    "getting_started": 0.14,
    "troubleshooting": 0.18,
    "integration": 0.08,
    "safety": 0.08,
}
HIGH_VALUE_SECTION_TERMS = {
    "getting started",
    "setup",
    "installation",
    "overview",
    "create a workspace",
    "first build",
    "running the example",
    "troubleshooting",
}
LOW_VALUE_SECTION_TERMS = {
    "see also",
    "additional resources",
    "further information",
    "next step",
}


class ChecklistWorkflow:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        retrieval_mode: str = "hybrid",
        evidence_top_k: int = 6,
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
        evidence_top_k: int = 6,
        llm_client: LLMClient | None = None,
        enable_llm_synthesis: bool = True,
    ) -> "ChecklistWorkflow":
        return cls(
            retrieval_service=RetrievalService.from_index_dir(index_dir),
            retrieval_mode=retrieval_mode,
            evidence_top_k=evidence_top_k,
            llm_client=llm_client,
            enable_llm_synthesis=enable_llm_synthesis,
        )

    def build_checklist(
        self,
        *,
        query: str | None = None,
        evidence_results: list[dict[str, Any]] | None = None,
    ) -> GroundedChecklist:
        normalized_query = (query or "").strip()
        if not normalized_query and not evidence_results:
            raise ValueError("Either query or evidence_results must be provided")

        route = infer_query_route(normalized_query) if normalized_query else None
        results = evidence_results
        if results is None:
            raw_top_k = max(self.evidence_top_k * 3, 12)
            results = self.retrieval_service.search(
                normalized_query,
                mode=self.retrieval_mode,
                top_k=raw_top_k,
            )

        selected_results = select_checklist_results(
            results or [],
            route=route,
            retrieval_mode=self.retrieval_mode,
            limit=self.evidence_top_k,
        )
        citations = build_checklist_citations(selected_results, self.retrieval_mode)
        if not selected_results:
            LOGGER.info("No retrieval results found for checklist query: %s", normalized_query)
            return build_insufficient_checklist(query=normalized_query, citations=[], confidence=0.0)

        fallback_checklist = build_rule_based_checklist(
            query=normalized_query,
            results=selected_results,
            citations=citations,
            retrieval_mode=self.retrieval_mode,
        )
        if fallback_checklist.status == "insufficient_evidence":
            return fallback_checklist

        llm_checklist = self._try_llm_synthesis(
            query=normalized_query or fallback_checklist.checklist_title,
            results=selected_results,
            citations=citations,
        )
        if llm_checklist is not None:
            return llm_checklist

        LOGGER.info("Falling back to rule-based grounded checklist for query: %s", normalized_query)
        return fallback_checklist

    def _try_llm_synthesis(
        self,
        *,
        query: str,
        results: list[dict[str, Any]],
        citations: list[Citation],
    ) -> GroundedChecklist | None:
        if not self.enable_llm_synthesis:
            LOGGER.info("LLM synthesis is disabled; using rule-based checklist fallback")
            return None
        if self.llm_client is None:
            LOGGER.info("No LLM client configured; using rule-based checklist fallback")
            return None

        try:
            user_prompt = build_grounded_checklist_user_prompt(query=query, evidence_results=results)
            llm_payload = self.llm_client.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            parsed_payload = LLMGroundedChecklistPayload.from_dict(llm_payload)
            return validate_and_build_llm_checklist(
                query=query,
                payload=parsed_payload,
                citations=citations,
            )
        except Exception as exc:
            LOGGER.warning("LLM checklist synthesis failed validation or request handling: %s", exc)
            return None


def build_rule_based_checklist(
    *,
    query: str,
    results: list[dict[str, Any]],
    citations: list[Citation],
    retrieval_mode: str,
) -> GroundedChecklist:
    prerequisites = extract_prerequisites(results)
    ordered_steps = extract_ordered_steps(results)
    warnings = extract_warnings(results)
    validation_checks = extract_validation_checks(results)
    checklist_title = build_checklist_title(query, results)

    if not has_sufficient_checklist_evidence(results, ordered_steps, citations):
        return build_insufficient_checklist(
            query=query,
            citations=citations,
            confidence=estimate_checklist_confidence(results, ordered_steps, sufficient=False),
        )

    return GroundedChecklist(
        query=query,
        checklist_title=checklist_title,
        prerequisites=prerequisites[:4],
        ordered_steps=ordered_steps[:6],
        warnings=warnings[:4],
        validation_checks=validation_checks[:4],
        status="grounded_checklist",
        confidence=estimate_checklist_confidence(results, ordered_steps, sufficient=True),
        citations=citations,
    )


def build_insufficient_checklist(
    *,
    query: str,
    citations: list[Citation],
    confidence: float,
) -> GroundedChecklist:
    return GroundedChecklist(
        query=query,
        checklist_title=INSUFFICIENT_TITLE,
        prerequisites=[],
        ordered_steps=[],
        warnings=[],
        validation_checks=[],
        status="insufficient_evidence",
        confidence=confidence,
        citations=citations,
    )


def validate_and_build_llm_checklist(
    *,
    query: str,
    payload: LLMGroundedChecklistPayload,
    citations: list[Citation],
) -> GroundedChecklist:
    used_citations = map_used_citation_ids(payload.used_citation_ids, citations)
    if payload.status == "grounded_checklist":
        if not payload.checklist_title.strip():
            raise ValueError("LLM grounded checklist must include a non-empty checklist_title")
        if not payload.ordered_steps:
            raise ValueError("LLM grounded checklist must include at least one ordered step")
        if not used_citations:
            raise ValueError("LLM grounded checklist must reference at least one valid citation id")

    title = payload.checklist_title.strip() or INSUFFICIENT_TITLE
    prerequisites = payload.prerequisites[:4]
    ordered_steps = payload.ordered_steps[:6]
    warnings = payload.warnings[:4]
    validation_checks = payload.validation_checks[:4]
    if payload.status == "insufficient_evidence":
        title = INSUFFICIENT_TITLE
        prerequisites = []
        ordered_steps = []
        warnings = []
        validation_checks = []

    return GroundedChecklist(
        query=query,
        checklist_title=title,
        prerequisites=prerequisites,
        ordered_steps=ordered_steps,
        warnings=warnings,
        validation_checks=validation_checks,
        status=payload.status,
        confidence=payload.confidence,
        citations=used_citations,
    )


def build_checklist_citations(results: list[dict[str, Any]], retrieval_mode: str) -> list[Citation]:
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


def select_checklist_results(
    results: list[dict[str, Any]],
    *,
    route: QueryRoute | None,
    retrieval_mode: str,
    limit: int,
) -> list[dict[str, Any]]:
    if not results:
        return []

    scored_results: list[dict[str, Any]] = []
    for index, result in enumerate(results):
        enriched = dict(result)
        enriched["_checklist_score"] = score_result_for_checklist(
            enriched,
            route=route,
            retrieval_mode=retrieval_mode,
            rank=index,
        )
        scored_results.append(enriched)

    scored_results.sort(
        key=lambda item: (
            float(item.get("_checklist_score", 0.0)),
            extract_display_score(item, retrieval_mode),
        ),
        reverse=True,
    )

    selected: list[dict[str, Any]] = []
    seen_section_keys: set[str] = set()
    page_counts: dict[str, int] = {}
    for result in scored_results:
        section_key = build_section_key(result)
        if section_key in seen_section_keys:
            continue

        url = str(result.get("url", "")).strip()
        if url and page_counts.get(url, 0) >= 2:
            continue

        seen_section_keys.add(section_key)
        if url:
            page_counts[url] = page_counts.get(url, 0) + 1
        selected.append(result)
        if len(selected) >= limit:
            break

    if selected:
        return selected
    return results[:limit]


def score_result_for_checklist(
    result: dict[str, Any],
    *,
    route: QueryRoute | None,
    retrieval_mode: str,
    rank: int,
) -> float:
    score = extract_display_score(result, retrieval_mode)
    doc_type = str(result.get("doc_type", "")).strip().lower()
    source = str(result.get("source", "")).strip()
    topic = str(result.get("topic", "")).strip().lower()
    title = str(result.get("title", "")).strip().lower()
    section_path = [str(item).strip().lower() for item in result.get("section_path", [])]
    combined_heading = " ".join([title, topic, " ".join(section_path)]).strip()

    score += CHECKLIST_DOC_TYPE_PRIORITIES.get(doc_type, 0.0)

    if any(term in combined_heading for term in HIGH_VALUE_SECTION_TERMS):
        score += 0.14
    if any(term in combined_heading for term in LOW_VALUE_SECTION_TERMS):
        score -= 0.18

    if route is not None:
        if source and source in route.preferred_sources:
            score += 0.2
        elif route.preferred_sources:
            score -= 0.12

        if doc_type in route.preferred_doc_types:
            type_rank = route.preferred_doc_types.index(doc_type)
            score += max(0.06, 0.16 - (type_rank * 0.03))

        keyword_overlap = count_keyword_overlap(route.topic_keywords, combined_heading)
        score += min(keyword_overlap * 0.04, 0.2)

        if route.intent == "troubleshooting" and doc_type == "troubleshooting":
            score += 0.08
        if route.intent == "procedural" and doc_type in {"installation", "tutorial", "getting_started"}:
            score += 0.08

    score += max(0.0, 0.03 - (rank * 0.003))
    return score


def count_keyword_overlap(keywords: list[str], combined_text: str) -> int:
    return sum(1 for keyword in keywords if keyword and keyword in combined_text)


def build_section_key(result: dict[str, Any]) -> str:
    url = str(result.get("url", "")).strip()
    section_path = [normalize_text(str(item)) for item in result.get("section_path", []) if str(item).strip()]
    if section_path:
        return f"{url}::{' > '.join(section_path)}"
    return url or str(result.get("chunk_id", "")).strip()


def build_checklist_title(query: str, results: list[dict[str, Any]]) -> str:
    if query:
        compact_query = " ".join(query.split())
        if len(compact_query) <= 110:
            return compact_query
    top_title = str(results[0].get("title", "")).strip() if results else ""
    top_sections = [str(item).strip() for item in results[0].get("section_path", []) if str(item).strip()] if results else []
    if top_title:
        if top_sections:
            return f"{top_title} - {top_sections[-1]} Checklist"
        return f"{top_title} Checklist"
    return "Grounded Engineering Checklist"


def extract_prerequisites(results: list[dict[str, Any]]) -> list[str]:
    return collect_checklist_items(results, hint_terms=PREREQUISITE_HINTS, limit=4)


def extract_ordered_steps(results: list[dict[str, Any]]) -> list[str]:
    steps: list[str] = []
    seen: set[str] = set()
    for result in results:
        for sentence in split_candidate_sentences(str(result.get("text", ""))):
            normalized = normalize_text(sentence)
            if normalized in seen:
                continue
            if looks_like_step(sentence):
                seen.add(normalized)
                steps.append(clean_sentence(sentence))
            if len(steps) >= 6:
                return steps
    return steps


def extract_warnings(results: list[dict[str, Any]]) -> list[str]:
    return collect_checklist_items(results, hint_terms=WARNING_HINTS, limit=4)


def extract_validation_checks(results: list[dict[str, Any]]) -> list[str]:
    checks = collect_checklist_items(results, hint_terms=VALIDATION_HINTS, limit=4)
    if checks:
        return checks

    fallback_checks: list[str] = []
    for result in results:
        title = str(result.get("title", "")).strip()
        section_path = [str(item).strip() for item in result.get("section_path", []) if str(item).strip()]
        if title:
            fallback_checks.append(f"Verify the outcome described in {title}.")
        elif section_path:
            fallback_checks.append(f"Verify the section {' > '.join(section_path)}.")
        if len(fallback_checks) >= 2:
            break
    return dedupe_preserve_order(fallback_checks)


def collect_checklist_items(
    results: list[dict[str, Any]],
    *,
    hint_terms: tuple[str, ...],
    limit: int,
) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for result in results:
        for sentence in split_candidate_sentences(str(result.get("text", ""))):
            normalized = normalize_text(sentence)
            if normalized in seen:
                continue
            if is_short_heading_label(sentence):
                continue
            if looks_like_non_action_heading(sentence):
                continue
            lowered = normalized
            if "without error" in lowered:
                continue
            if any(term in lowered for term in hint_terms):
                cleaned = clean_sentence(sentence)
                if cleaned:
                    seen.add(normalized)
                    items.append(cleaned)
            if len(items) >= limit:
                return items
    return items


def split_candidate_sentences(text: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        raw_pieces = [line] if COMMAND_RE.match(line) else SENTENCE_SPLIT_RE.split(line)
        for raw_piece in raw_pieces:
            piece = clean_sentence(raw_piece)
            if not piece:
                continue
            lowered = piece.lower()
            if any(pattern in lowered for pattern in NOISE_PATTERNS):
                continue
            if len(piece) < 12 and not COMMAND_RE.match(piece):
                continue
            candidates.append(piece)
    return candidates


def clean_sentence(text: str) -> str:
    cleaned = HEADING_RE.sub("", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def looks_like_step(text: str) -> bool:
    stripped = text.strip()
    lowered = stripped.lower()
    if COMMAND_RE.match(stripped):
        return True
    if is_short_heading_label(stripped):
        return False
    if looks_like_non_action_heading(stripped):
        return False
    if lowered.startswith(ACTION_PREFIXES):
        return True
    if any(term in lowered for term in PROCEDURE_HINTS):
        return True
    return False


def looks_like_non_action_heading(text: str) -> bool:
    stripped = clean_sentence(text)
    if not stripped:
        return False
    lowered = stripped.lower()
    if COMMAND_RE.match(stripped):
        return False
    if lowered.startswith(ACTION_PREFIXES):
        return False
    if any(token in lowered for token in (".", ";", ":", "$", "/", "\\")):
        return False

    words = stripped.split()
    if len(words) > 8:
        return False
    if stripped == stripped.upper():
        return True
    if stripped == stripped.title() and not any(term in lowered for term in PROCEDURE_HINTS):
        return True
    return False


def is_short_heading_label(text: str) -> bool:
    stripped = clean_sentence(text)
    if not stripped:
        return False
    if COMMAND_RE.match(stripped):
        return False
    if any(token in stripped for token in ".:;!?$\\/"):
        return False
    words = stripped.split()
    if len(words) > 3:
        return False
    return stripped == stripped.title() or stripped == stripped.upper()


def has_sufficient_checklist_evidence(
    results: list[dict[str, Any]],
    ordered_steps: list[str],
    citations: list[Citation],
) -> bool:
    if len(ordered_steps) >= 2 and len(citations) >= 2:
        return True
    if results and extract_display_score(results[0], "hybrid") >= 0.4 and len(ordered_steps) >= 1:
        return True
    return False


def estimate_checklist_confidence(
    results: list[dict[str, Any]],
    ordered_steps: list[str],
    *,
    sufficient: bool,
) -> float:
    if not results:
        return 0.0
    top_score = extract_display_score(results[0], "hybrid")
    step_factor = min(len(ordered_steps), 4) * 0.08
    score_factor = min(top_score * 1.2, 0.5)
    base = 0.18 if sufficient else 0.05
    confidence = base + step_factor + score_factor
    if not sufficient:
        confidence = min(confidence, 0.4)
    return max(0.0, min(confidence, 0.9))


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


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def build_checklist_workflow(
    *,
    index_dir: Path,
    retrieval_mode: str = "hybrid",
    evidence_top_k: int = 6,
    llm_client: LLMClient | None = None,
    enable_llm_synthesis: bool = True,
) -> ChecklistWorkflow:
    return ChecklistWorkflow.from_index_dir(
        index_dir,
        retrieval_mode=retrieval_mode,
        evidence_top_k=evidence_top_k,
        llm_client=llm_client,
        enable_llm_synthesis=enable_llm_synthesis,
    )
