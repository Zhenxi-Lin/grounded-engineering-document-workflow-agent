from __future__ import annotations

import re
from typing import Any

from app.retrieval.query_router import QueryRoute

SECTION_BOOST_TERMS = [
    "getting started",
    "setup",
    "installation",
    "overview",
    "create a workspace",
    "first build",
    "running the example",
    "troubleshooting",
]
SECTION_DOWNWEIGHT_TERMS = [
    "see also",
    "additional resources",
    "further information",
    "next step",
]


def rerank_results(
    results: list[dict[str, Any]],
    *,
    route: QueryRoute,
    top_k: int,
    max_per_url: int = 1,
) -> list[dict[str, Any]]:
    scored = [apply_metadata_boost(result, route=route) for result in results]
    scored.sort(key=lambda item: item["final_score"], reverse=True)
    return diversify_results(scored, top_k=top_k, max_per_url=max_per_url)


def apply_metadata_boost(result: dict[str, Any], *, route: QueryRoute) -> dict[str, Any]:
    boosted = dict(result)
    base_score = float(boosted.get("hybrid_score", 0.0))
    metadata_bonus = 0.0
    boost_reasons: list[str] = []

    source = str(boosted.get("source", ""))
    doc_type = str(boosted.get("doc_type", ""))
    title = str(boosted.get("title", ""))
    topic = str(boosted.get("topic", ""))
    section_path = [str(item) for item in boosted.get("section_path", [])]
    combined_text = " ".join([title, topic, " ".join(section_path)]).lower()

    if source in route.preferred_sources:
        source_rank = route.preferred_sources.index(source)
        source_bonus = max(0.18 - 0.04 * source_rank, 0.06)
        metadata_bonus += source_bonus
        boost_reasons.append(f"source:{source_bonus:.2f}")

    if doc_type in route.preferred_doc_types:
        type_rank = route.preferred_doc_types.index(doc_type)
        type_bonus = max(0.16 - 0.03 * type_rank, 0.05)
        metadata_bonus += type_bonus
        boost_reasons.append(f"doc_type:{type_bonus:.2f}")

    keyword_overlap = count_keyword_overlap(route.topic_keywords, combined_text)
    if keyword_overlap > 0:
        keyword_bonus = min(keyword_overlap * 0.03, 0.15)
        metadata_bonus += keyword_bonus
        boost_reasons.append(f"topic_overlap:{keyword_bonus:.2f}")

    section_bonus = score_section_quality(combined_text)
    if section_bonus != 0.0:
        metadata_bonus += section_bonus
        boost_reasons.append(f"section_quality:{section_bonus:.2f}")

    if route.intent == "troubleshooting" and contains_any(
        combined_text,
        ["troubleshoot", "compatibility", "failsafe", "safety", "error", "debug"],
    ):
        metadata_bonus += 0.08
        boost_reasons.append("intent_match:0.08")
    elif route.intent == "procedural" and contains_any(
        combined_text,
        ["install", "setup", "tutorial", "getting started", "build", "run", "launch"],
    ):
        metadata_bonus += 0.08
        boost_reasons.append("intent_match:0.08")
    elif route.intent == "factual" and contains_any(
        combined_text,
        ["concept", "overview", "architecture", "reference", "discovery", "qos"],
    ):
        metadata_bonus += 0.08
        boost_reasons.append("intent_match:0.08")

    boosted["metadata_bonus"] = metadata_bonus
    boosted["final_score"] = base_score + metadata_bonus
    boosted["ranking_debug"] = {
        "base_score": base_score,
        "metadata_bonus": metadata_bonus,
        "boost_reasons": boost_reasons,
        "route_intent": route.intent,
        "route_sources": route.preferred_sources,
        "route_doc_types": route.preferred_doc_types,
    }
    return boosted


def diversify_results(
    results: list[dict[str, Any]],
    *,
    top_k: int,
    max_per_url: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    overflow: list[dict[str, Any]] = []
    url_counts: dict[str, int] = {}
    seen_section_keys: set[str] = set()

    for result in results:
        url = str(result.get("url", ""))
        section_key = build_section_key(result)

        if section_key in seen_section_keys:
            continue

        if url_counts.get(url, 0) >= max_per_url:
            overflow.append(result)
            continue

        selected.append(result)
        seen_section_keys.add(section_key)
        url_counts[url] = url_counts.get(url, 0) + 1
        if len(selected) >= top_k:
            return selected

    for result in overflow:
        section_key = build_section_key(result)
        if section_key in seen_section_keys:
            continue
        selected.append(result)
        seen_section_keys.add(section_key)
        if len(selected) >= top_k:
            break

    return selected


def build_section_key(result: dict[str, Any]) -> str:
    url = str(result.get("url", ""))
    section_path = [normalize_key_text(item) for item in result.get("section_path", [])]
    if section_path:
        return f"{url}::{' > '.join(section_path)}"
    title = normalize_key_text(result.get("title", ""))
    preview = normalize_key_text(result.get("text", ""))[:120]
    return f"{url}::{title}::{preview}"


def count_keyword_overlap(keywords: list[str], combined_text: str) -> int:
    return sum(1 for keyword in keywords if keyword in combined_text)


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term in text for term in terms)


def score_section_quality(text: str) -> float:
    bonus = 0.0
    for term in SECTION_BOOST_TERMS:
        if term in text:
            bonus += 0.05
    for term in SECTION_DOWNWEIGHT_TERMS:
        if term in text:
            bonus -= 0.08
    return max(-0.16, min(bonus, 0.16))


def normalize_key_text(value: Any) -> str:
    text = str(value).lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text
