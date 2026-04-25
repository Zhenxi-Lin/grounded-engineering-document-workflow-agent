from __future__ import annotations

import re
from dataclasses import asdict, dataclass


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "can",
    "could",
    "do",
    "does",
    "for",
    "from",
    "how",
    "i",
    "in",
    "is",
    "it",
    "me",
    "my",
    "of",
    "on",
    "or",
    "should",
    "the",
    "their",
    "them",
    "to",
    "using",
    "what",
    "when",
    "why",
    "with",
}

TOKEN_RE = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class QueryRoute:
    intent: str
    preferred_sources: list[str]
    preferred_doc_types: list[str]
    topic_keywords: list[str]
    routing_debug: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def infer_query_route(query: str) -> QueryRoute:
    normalized_query = query.strip().lower()
    tokens = extract_query_keywords(normalized_query)
    intent = infer_intent(normalized_query)
    preferred_sources = infer_preferred_sources(normalized_query)
    preferred_doc_types = infer_preferred_doc_types(normalized_query, intent)

    routing_debug = {
        "matched_intent": intent,
        "matched_sources": preferred_sources,
        "matched_doc_types": preferred_doc_types,
        "topic_keywords": tokens,
    }
    return QueryRoute(
        intent=intent,
        preferred_sources=preferred_sources,
        preferred_doc_types=preferred_doc_types,
        topic_keywords=tokens,
        routing_debug=routing_debug,
    )


def infer_intent(query: str) -> str:
    strong_troubleshooting_terms = [
        "fail",
        "failing",
        "error",
        "wrong",
        "issue",
        "issues",
        "unable",
        "not receiving",
        "not publishing",
        "mismatch",
        "overflow",
        "fix",
        "debug",
        "troubleshoot",
        "why isn't",
        "why is",
    ]
    if any(term in query for term in strong_troubleshooting_terms):
        return "troubleshooting"

    if any(term in query for term in ["problem", "problems"]):
        if not query.startswith("what is ") and "what problem is" not in query:
            return "troubleshooting"

    procedural_terms = [
        "how do i",
        "how to",
        "steps",
        "install",
        "setup",
        "set up",
        "configure",
        "build",
        "create",
        "run",
        "launch",
        "start",
    ]
    if any(term in query for term in procedural_terms):
        return "procedural"

    return "factual"


def infer_preferred_sources(query: str) -> list[str]:
    sources: list[str] = []

    if "isaac ros" in query:
        sources.append("Isaac ROS docs")
    if "moveit" in query:
        sources.append("MoveIt docs")
    if "px4" in query:
        sources.append("PX4 official docs")
    if any(term in query for term in ["ros 2", "ros2"]):
        sources.append("ROS 2 official docs")

    if any(term in query for term in ["qgroundcontrol", "uxrce", "uorb", "failsafe", "offboard"]):
        sources.append("PX4 official docs")
    if any(term in query for term in ["colcon", "qos", "discovery", "ros2doctor"]):
        sources.append("ROS 2 official docs")
    if any(term in query for term in ["planning scene", "moveitcpp", "rviz", "controller configuration"]):
        sources.append("MoveIt docs")
    if any(term in query for term in ["isaac", "nitros", "cumotion", "visual slam", "jetson", "dgx"]):
        sources.append("Isaac ROS docs")

    if not sources:
        if any(term in query for term in ["motion planning", "planning results", "planning"]):
            sources.append("MoveIt docs")
        elif any(term in query for term in ["supported platform", "accelerated", "cuda"]):
            sources.append("Isaac ROS docs")

    return dedupe_preserve_order(sources)


def infer_preferred_doc_types(query: str, intent: str) -> list[str]:
    if intent == "procedural":
        doc_types = ["installation", "tutorial", "getting_started"]
    elif intent == "troubleshooting":
        doc_types = ["troubleshooting", "safety", "integration"]
    else:
        doc_types = ["concept", "reference", "integration"]

    if any(term in query for term in ["safety", "failsafe", "geofence", "arming"]):
        doc_types = ["safety"] + doc_types
    if any(term in query for term in ["compatibility", "bridge", "offboard", "frame convention", "qos"]):
        doc_types = ["integration"] + doc_types
    if any(term in query for term in ["getting started", "beginner tutorials"]):
        doc_types = ["getting_started", "installation", "tutorial"] + doc_types

    return dedupe_preserve_order(doc_types)


def extract_query_keywords(query: str) -> list[str]:
    tokens = TOKEN_RE.findall(query.lower())
    filtered = [token for token in tokens if token not in STOPWORDS and len(token) > 2]
    return dedupe_preserve_order(filtered[:12])


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
