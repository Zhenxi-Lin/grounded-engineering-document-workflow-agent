from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.compare_parser import ComparisonTargets, parse_comparison_query, normalize_target
from app.llm_client import LLMClient
from app.models.answer_models import Citation
from app.models.compare_models import GroundedComparison, LLMGroundedComparisonPayload
from app.prompts.grounded_compare import SYSTEM_PROMPT, build_grounded_compare_user_prompt
from app.retrieval.query_router import STOPWORDS
from app.retrieval.retrieval_service import RetrievalService, extract_display_score, format_result_preview


LOGGER = logging.getLogger(__name__)

INSUFFICIENT_SUMMARY = "Available evidence was not sufficient to support a grounded comparison."
TOKEN_RE = re.compile(r"[a-z0-9_]+")
GENERIC_TARGET_TOKENS = {"ros", "docs", "official", "guide"}


@dataclass(frozen=True)
class GroupedEvidence:
    targets: ComparisonTargets
    side_a_results: list[dict[str, Any]]
    side_b_results: list[dict[str, Any]]
    shared_results: list[dict[str, Any]]
    side_a_scores: dict[str, float]
    side_b_scores: dict[str, float]


LOW_VALUE_SECTION_TERMS = {
    "see also",
    "additional resources",
    "further information",
    "next step",
}


class CompareWorkflow:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        retrieval_mode: str = "hybrid",
        evidence_top_k: int = 8,
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
        evidence_top_k: int = 8,
        llm_client: LLMClient | None = None,
        enable_llm_synthesis: bool = True,
    ) -> "CompareWorkflow":
        return cls(
            retrieval_service=RetrievalService.from_index_dir(index_dir),
            retrieval_mode=retrieval_mode,
            evidence_top_k=evidence_top_k,
            llm_client=llm_client,
            enable_llm_synthesis=enable_llm_synthesis,
        )

    def compare(self, query: str) -> GroundedComparison:
        normalized_query = query.strip()
        if not normalized_query:
            raise ValueError("Query cannot be empty")

        parse_result = parse_comparison_query(normalized_query)
        if not parse_result.success:
            LOGGER.warning(
                "Could not infer two comparison targets from query '%s': %s",
                normalized_query,
                parse_result.failure_reason or "unknown parser failure",
            )
            return build_insufficient_comparison(
                query=normalized_query,
                citations=[],
                confidence=0.0,
            )
        targets = parse_result.to_targets()

        results = retrieve_comparison_results(
            retrieval_service=self.retrieval_service,
            query=normalized_query,
            targets=targets,
            retrieval_mode=self.retrieval_mode,
            evidence_top_k=self.evidence_top_k,
        )
        if not results:
            LOGGER.info("No retrieval results found for comparison query: %s", normalized_query)
            return build_insufficient_comparison(
                query=normalized_query,
                citations=[],
                confidence=0.0,
            )

        grouped = group_evidence_by_targets(results, targets)
        relevant_results = select_relevant_results(grouped)
        citations = build_compare_citations(relevant_results, self.retrieval_mode)
        if not has_sufficient_comparison_evidence(grouped):
            LOGGER.info("Comparison evidence insufficient for query: %s", normalized_query)
            return build_insufficient_comparison(
                query=normalized_query,
                citations=citations,
                confidence=estimate_compare_confidence(grouped, sufficient=False),
            )

        fallback_comparison = build_rule_based_comparison(
            query=normalized_query,
            grouped=grouped,
            citations=citations,
        )
        if fallback_comparison.status == "insufficient_evidence":
            return fallback_comparison

        llm_comparison = self._try_llm_synthesis(
            query=normalized_query,
            grouped=grouped,
            evidence_results=relevant_results,
            citations=citations,
        )
        if llm_comparison is not None:
            return llm_comparison

        LOGGER.info("Falling back to rule-based grounded comparison for query: %s", normalized_query)
        return fallback_comparison

    def _try_llm_synthesis(
        self,
        *,
        query: str,
        grouped: GroupedEvidence,
        evidence_results: list[dict[str, Any]],
        citations: list[Citation],
    ) -> GroundedComparison | None:
        if not self.enable_llm_synthesis:
            LOGGER.info("LLM synthesis is disabled; using rule-based comparison fallback")
            return None
        if self.llm_client is None:
            LOGGER.info("No LLM client configured; using rule-based comparison fallback")
            return None

        try:
            user_prompt = build_grounded_compare_user_prompt(
                query=query,
                target_a=grouped.targets.side_a,
                target_b=grouped.targets.side_b,
                evidence_results=evidence_results,
            )
            llm_payload = self.llm_client.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            parsed_payload = LLMGroundedComparisonPayload.from_dict(llm_payload)
            return validate_and_build_llm_comparison(
                query=query,
                payload=parsed_payload,
                citations=citations,
            )
        except Exception as exc:
            LOGGER.warning("LLM comparison synthesis failed validation or request handling: %s", exc)
            return None
def retrieve_comparison_results(
    *,
    retrieval_service: RetrievalService,
    query: str,
    targets: ComparisonTargets,
    retrieval_mode: str,
    evidence_top_k: int,
) -> list[dict[str, Any]]:
    query_results = retrieval_service.search(
        query,
        mode=retrieval_mode,
        top_k=evidence_top_k,
    )
    per_side_top_k = max(2, min(4, evidence_top_k // 2))
    side_a_results = retrieval_service.search(
        targets.side_a,
        mode=retrieval_mode,
        top_k=per_side_top_k,
    )
    side_b_results = retrieval_service.search(
        targets.side_b,
        mode=retrieval_mode,
        top_k=per_side_top_k,
    )
    return merge_results(query_results, side_a_results, side_b_results)


def merge_results(*result_lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for results in result_lists:
        for result in results:
            chunk_id = str(result.get("chunk_id", ""))
            if not chunk_id or chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(chunk_id)
            merged.append(result)
    return merged


def group_evidence_by_targets(
    results: list[dict[str, Any]],
    targets: ComparisonTargets,
) -> GroupedEvidence:
    side_a_results: list[dict[str, Any]] = []
    side_b_results: list[dict[str, Any]] = []
    shared_results: list[dict[str, Any]] = []
    side_a_scores: dict[str, float] = {}
    side_b_scores: dict[str, float] = {}

    for result in results:
        score_a = score_result_for_target(result, targets.side_a)
        score_b = score_result_for_target(result, targets.side_b)
        chunk_id = str(result.get("chunk_id", ""))
        side_a_scores[chunk_id] = score_a
        side_b_scores[chunk_id] = score_b

        if score_a <= 0 and score_b <= 0:
            continue
        if score_a > 0 and score_b > 0 and abs(score_a - score_b) <= 0.75:
            shared_results.append(result)
        elif score_a >= score_b:
            side_a_results.append(result)
        else:
            side_b_results.append(result)

    side_a_results = filter_low_value_tail(side_a_results, side_a_scores)
    side_b_results = filter_low_value_tail(side_b_results, side_b_scores)
    shared_results = filter_low_value_tail(
        shared_results,
        {
            str(result.get("chunk_id", "")): max(
                side_a_scores.get(str(result.get("chunk_id", "")), 0.0),
                side_b_scores.get(str(result.get("chunk_id", "")), 0.0),
            )
            for result in shared_results
        },
    )

    side_a_results.sort(
        key=lambda result: (
            side_a_scores.get(str(result.get("chunk_id", "")), 0.0),
            extract_display_score(result, "hybrid"),
        ),
        reverse=True,
    )
    side_b_results.sort(
        key=lambda result: (
            side_b_scores.get(str(result.get("chunk_id", "")), 0.0),
            extract_display_score(result, "hybrid"),
        ),
        reverse=True,
    )
    shared_results.sort(
        key=lambda result: (
            max(
                side_a_scores.get(str(result.get("chunk_id", "")), 0.0),
                side_b_scores.get(str(result.get("chunk_id", "")), 0.0),
            ),
            extract_display_score(result, "hybrid"),
        ),
        reverse=True,
    )

    return GroupedEvidence(
        targets=targets,
        side_a_results=side_a_results,
        side_b_results=side_b_results,
        shared_results=shared_results,
        side_a_scores=side_a_scores,
        side_b_scores=side_b_scores,
    )


def score_result_for_target(result: dict[str, Any], target: str) -> float:
    combined_text = " ".join(
        [
            str(result.get("title", "")),
            str(result.get("source", "")),
            str(result.get("doc_type", "")),
            str(result.get("topic", "")),
            " ".join(str(item) for item in result.get("section_path", [])),
            format_result_preview(str(result.get("text", "")), max_chars=320),
        ]
    ).lower()

    target_terms = build_target_terms(target)
    if not target_terms:
        return 0.0

    score = 0.0
    for term in target_terms:
        if term in combined_text:
            if " " in term:
                score += 1.5
            else:
                score += 1.0
    return score


def build_target_terms(target: str) -> list[str]:
    normalized = normalize_target(target)
    tokens = [token for token in TOKEN_RE.findall(normalized) if token not in STOPWORDS]
    terms: list[str] = [normalized]

    if normalized == "ros 2":
        terms.extend(["ros2", "ros 2"])
    if normalized == "isaac ros":
        terms.extend(["isaac ros", "isaac"])
    if len(tokens) == 1:
        terms.extend(tokens)
    elif len(tokens) > 1:
        terms.extend(
            token
            for token in tokens
            if token not in GENERIC_TARGET_TOKENS and len(token) >= 4
        )
    return dedupe_preserve_order([term for term in terms if term and len(term) >= 2])


def normalize_target(target: str) -> str:
    return " ".join(target.lower().split())


def has_sufficient_comparison_evidence(grouped: GroupedEvidence) -> bool:
    side_a_meaningful = collect_meaningful_side_results(grouped.side_a_results, grouped.side_a_scores)
    side_b_meaningful = collect_meaningful_side_results(grouped.side_b_results, grouped.side_b_scores)
    shared_meaningful = collect_meaningful_shared_results(grouped)

    support_a = side_a_meaningful or shared_meaningful
    support_b = side_b_meaningful or shared_meaningful
    if not support_a or not support_b:
        return False

    total_support = len(collect_supported_chunk_ids(side_a_meaningful, side_b_meaningful, shared_meaningful))
    if total_support < 2:
        return False

    side_a_top = strongest_supported_score(
        side_a_meaningful,
        grouped.side_a_scores,
        shared_meaningful,
        grouped.side_a_scores,
    )
    side_b_top = strongest_supported_score(
        side_b_meaningful,
        grouped.side_b_scores,
        shared_meaningful,
        grouped.side_b_scores,
    )
    return side_a_top >= 0.8 and side_b_top >= 0.8


def strongest_side_score(results: list[dict[str, Any]], score_map: dict[str, float]) -> float:
    if not results:
        return 0.0
    return max(score_map.get(str(result.get("chunk_id", "")), 0.0) for result in results)


def select_relevant_results(grouped: GroupedEvidence) -> list[dict[str, Any]]:
    if grouped.shared_results and (not grouped.side_a_results or not grouped.side_b_results):
        selected = grouped.shared_results[:2] + grouped.side_a_results[:2] + grouped.side_b_results[:2]
    elif grouped.shared_results:
        selected = grouped.shared_results[:2] + grouped.side_a_results[:1] + grouped.side_b_results[:1]
    else:
        selected = grouped.side_a_results[:2] + grouped.side_b_results[:2]
    deduped: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()
    for result in selected:
        chunk_id = str(result.get("chunk_id", ""))
        if chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(chunk_id)
        deduped.append(result)
    return deduped


def build_compare_citations(results: list[dict[str, Any]], retrieval_mode: str) -> list[Citation]:
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


def build_summary(grouped: GroupedEvidence) -> str:
    if grouped.shared_results:
        shared_anchor = describe_result_anchor(grouped.shared_results[0])
        return (
            f"The retrieved evidence compares {grouped.targets.side_a} and {grouped.targets.side_b}. "
            f"The strongest direct comparison evidence appears in {shared_anchor}."
        )

    a_focus = describe_side_focus(grouped.targets.side_a, grouped.side_a_results[:1])
    b_focus = describe_side_focus(grouped.targets.side_b, grouped.side_b_results[:1])
    if not a_focus or not b_focus:
        return ""
    return (
        f"The retrieved evidence compares {grouped.targets.side_a} and {grouped.targets.side_b}. "
        f"Evidence for {grouped.targets.side_a} centers on {a_focus}, while evidence for "
        f"{grouped.targets.side_b} centers on {b_focus}."
    )


def build_common_points(grouped: GroupedEvidence) -> list[str]:
    points: list[str] = []

    shared_doc_types = intersect_values(grouped.side_a_results, grouped.side_b_results, "doc_type")
    if shared_doc_types:
        points.append(
            f"Both sides are mainly documented through {', '.join(shared_doc_types[:2])} material."
        )

    shared_sources = intersect_values(grouped.side_a_results, grouped.side_b_results, "source")
    if shared_sources:
        points.append(
            f"Both sides appear in {', '.join(shared_sources[:2])}, which suggests the comparison is discussed within the same documentation domain."
        )

    if grouped.shared_results:
        shared_title = str(grouped.shared_results[0].get("title", "")).strip()
        if shared_title:
            points.append(
                f"There is shared evidence that touches both sides in the section titled '{shared_title}'."
            )

    if not points:
        points.append("Both sides have direct retrieved evidence, so the comparison is grounded in the current corpus.")

    return points[:3]


def build_differences(grouped: GroupedEvidence) -> list[str]:
    differences: list[str] = []

    if grouped.shared_results:
        differences.append(
            f"The most direct retrieved comparison between {grouped.targets.side_a} and {grouped.targets.side_b} appears in {describe_result_anchor(grouped.shared_results[0])}."
        )
    else:
        a_result = grouped.side_a_results[0] if grouped.side_a_results else None
        b_result = grouped.side_b_results[0] if grouped.side_b_results else None
        if a_result and b_result:
            differences.append(
                f"{grouped.targets.side_a} is primarily associated with {describe_result_anchor(a_result)}, while {grouped.targets.side_b} is primarily associated with {describe_result_anchor(b_result)}."
            )

    a_doc_type = top_value(grouped.side_a_results, "doc_type")
    b_doc_type = top_value(grouped.side_b_results, "doc_type")
    if a_doc_type and b_doc_type and a_doc_type != b_doc_type:
        differences.append(
            f"{grouped.targets.side_a} is retrieved mostly from {a_doc_type} content, whereas {grouped.targets.side_b} is retrieved mostly from {b_doc_type} content."
        )

    a_source = top_value(grouped.side_a_results, "source")
    b_source = top_value(grouped.side_b_results, "source")
    if a_source and b_source and a_source != b_source:
        differences.append(
            f"{grouped.targets.side_a} evidence comes mainly from {a_source}, while {grouped.targets.side_b} evidence comes mainly from {b_source}."
        )

    return differences[:3]


def build_risks_or_implications(grouped: GroupedEvidence) -> list[str]:
    risks: list[str] = []

    versions = collect_versions(grouped.side_a_results + grouped.side_b_results + grouped.shared_results)
    if len(versions) > 1:
        risks.append(
            f"The evidence spans multiple versions ({', '.join(versions[:3])}), so version-specific behavior should be verified before applying the comparison."
        )

    all_doc_types = collect_values(grouped.side_a_results + grouped.side_b_results + grouped.shared_results, "doc_type")
    if any(doc_type in {"troubleshooting", "safety", "integration"} for doc_type in all_doc_types):
        risks.append(
            "The retrieved evidence includes troubleshooting, safety, or integration material, so implementation choices may have compatibility or operational implications."
        )

    sources = collect_values(grouped.side_a_results + grouped.side_b_results, "source")
    if len(sources) > 1:
        risks.append(
            "The comparison crosses documentation domains, so terminology and assumptions may differ across sources."
        )

    if not risks:
        risks.append("The main implication is to verify the exact section and version before applying one side's guidance to the other.")

    return risks[:3]


def build_insufficient_comparison(
    *,
    query: str,
    citations: list[Citation],
    confidence: float,
) -> GroundedComparison:
    return GroundedComparison(
        query=query,
        summary=INSUFFICIENT_SUMMARY,
        common_points=[],
        differences=[],
        risks_or_implications=[],
        status="insufficient_evidence",
        confidence=confidence,
        citations=citations,
    )


def build_rule_based_comparison(
    *,
    query: str,
    grouped: GroupedEvidence,
    citations: list[Citation],
) -> GroundedComparison:
    summary = build_summary(grouped)
    common_points = build_common_points(grouped)
    differences = build_differences(grouped)
    risks = build_risks_or_implications(grouped)

    if not summary or not differences:
        LOGGER.info("Could not build a stable comparison skeleton for query: %s", query)
        return build_insufficient_comparison(
            query=query,
            citations=citations,
            confidence=estimate_compare_confidence(grouped, sufficient=False),
        )

    return GroundedComparison(
        query=query,
        summary=summary,
        common_points=common_points,
        differences=differences,
        risks_or_implications=risks,
        status="grounded_comparison",
        confidence=estimate_compare_confidence(grouped, sufficient=True),
        citations=citations,
    )


def validate_and_build_llm_comparison(
    *,
    query: str,
    payload: LLMGroundedComparisonPayload,
    citations: list[Citation],
) -> GroundedComparison:
    if payload.status == "grounded_comparison":
        if not payload.summary.strip():
            raise ValueError("LLM grounded comparison must include a non-empty summary")
        if not payload.differences:
            raise ValueError("LLM grounded comparison must include at least one difference")

    used_citations = map_used_citation_ids(payload.used_citation_ids, citations)
    if payload.status == "grounded_comparison" and not used_citations:
        raise ValueError("LLM grounded comparison must reference at least one valid citation id")

    summary = payload.summary.strip() or INSUFFICIENT_SUMMARY
    common_points = payload.common_points[:3]
    differences = payload.differences[:3]
    risks = payload.risks_or_implications[:3]

    if payload.status == "insufficient_evidence":
        summary = INSUFFICIENT_SUMMARY
        common_points = []
        differences = []
        risks = []

    return GroundedComparison(
        query=query,
        summary=summary,
        common_points=common_points,
        differences=differences,
        risks_or_implications=risks,
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


def describe_side_focus(side_label: str, results: list[dict[str, Any]]) -> str:
    if not results:
        return ""
    return describe_result_anchor(results[0])


def describe_result_anchor(result: dict[str, Any]) -> str:
    title = str(result.get("title", "")).strip()
    section_path = [str(item).strip() for item in result.get("section_path", []) if str(item).strip()]
    if len(section_path) >= 2:
        return f"the '{section_path[-1]}' section under '{title}'"
    if title:
        return f"the '{title}' page"
    return "a directly matched evidence chunk"


def intersect_values(
    side_a_results: list[dict[str, Any]],
    side_b_results: list[dict[str, Any]],
    key: str,
) -> list[str]:
    values_a = set(collect_values(side_a_results, key))
    values_b = set(collect_values(side_b_results, key))
    shared = [value for value in values_a.intersection(values_b) if value]
    return sorted(shared)


def collect_values(results: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for result in results:
        value = str(result.get(key, "")).strip()
        if value:
            values.append(value)
    return dedupe_preserve_order(values)


def collect_versions(results: list[dict[str, Any]]) -> list[str]:
    return collect_values(results, "version")


def top_value(results: list[dict[str, Any]], key: str) -> str:
    for result in results:
        value = str(result.get(key, "")).strip()
        if value:
            return value
    return ""


def estimate_compare_confidence(grouped: GroupedEvidence, *, sufficient: bool) -> float:
    side_a_strength = strongest_side_score(grouped.side_a_results, grouped.side_a_scores)
    side_b_strength = strongest_side_score(grouped.side_b_results, grouped.side_b_scores)
    retrieved_support = min(len(grouped.side_a_results) + len(grouped.side_b_results) + len(grouped.shared_results), 5)
    base = 0.2 if sufficient else 0.05
    confidence = base + min((side_a_strength + side_b_strength) * 0.14, 0.45) + retrieved_support * 0.05
    if not sufficient:
        confidence = min(confidence, 0.4)
    return max(0.0, min(confidence, 0.88))


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def filter_low_value_tail(
    results: list[dict[str, Any]],
    score_map: dict[str, float],
) -> list[dict[str, Any]]:
    if len(results) <= 1:
        return results

    filtered: list[dict[str, Any]] = []
    for result in results:
        chunk_id = str(result.get("chunk_id", ""))
        score = score_map.get(chunk_id, 0.0)
        if is_low_value_section(result) and score < 1.5:
            continue
        filtered.append(result)

    return filtered or results[:1]


def collect_meaningful_side_results(
    results: list[dict[str, Any]],
    score_map: dict[str, float],
) -> list[dict[str, Any]]:
    meaningful: list[dict[str, Any]] = []
    for result in results:
        chunk_id = str(result.get("chunk_id", ""))
        score = score_map.get(chunk_id, 0.0)
        if score < 0.8:
            continue
        if is_low_value_section(result) and score < 1.5:
            continue
        meaningful.append(result)
    return meaningful


def collect_meaningful_shared_results(grouped: GroupedEvidence) -> list[dict[str, Any]]:
    meaningful: list[dict[str, Any]] = []
    for result in grouped.shared_results:
        chunk_id = str(result.get("chunk_id", ""))
        max_score = max(
            grouped.side_a_scores.get(chunk_id, 0.0),
            grouped.side_b_scores.get(chunk_id, 0.0),
        )
        if max_score < 0.8:
            continue
        if is_low_value_section(result) and max_score < 1.5:
            continue
        meaningful.append(result)
    return meaningful


def collect_supported_chunk_ids(*result_groups: list[dict[str, Any]]) -> set[str]:
    chunk_ids: set[str] = set()
    for results in result_groups:
        for result in results[:2]:
            chunk_id = str(result.get("chunk_id", ""))
            if chunk_id:
                chunk_ids.add(chunk_id)
    return chunk_ids


def strongest_supported_score(
    primary_results: list[dict[str, Any]],
    primary_scores: dict[str, float],
    shared_results: list[dict[str, Any]],
    shared_scores: dict[str, float],
) -> float:
    primary_score = strongest_side_score(primary_results, primary_scores)
    shared_score = strongest_side_score(shared_results, shared_scores)
    return max(primary_score, shared_score)


def is_low_value_section(result: dict[str, Any]) -> bool:
    title = str(result.get("title", "")).lower()
    section_path = " ".join(str(item).lower() for item in result.get("section_path", []))
    combined = f"{title} {section_path}"
    return any(term in combined for term in LOW_VALUE_SECTION_TERMS)


def build_compare_workflow(
    *,
    index_dir: Path,
    retrieval_mode: str = "hybrid",
    evidence_top_k: int = 8,
    llm_client: LLMClient | None = None,
    enable_llm_synthesis: bool = True,
) -> CompareWorkflow:
    return CompareWorkflow.from_index_dir(
        index_dir,
        retrieval_mode=retrieval_mode,
        evidence_top_k=evidence_top_k,
        llm_client=llm_client,
        enable_llm_synthesis=enable_llm_synthesis,
    )
