from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


ALLOWED_ANSWER_STATUSES = {"grounded_answer", "insufficient_evidence"}


@dataclass(frozen=True)
class Citation:
    chunk_id: str
    title: str
    source: str
    version: str
    section_path: list[str]
    url: str
    score: float
    snippet: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class GroundedAnswer:
    query: str
    answer: str
    status: str
    confidence: float
    citations: list[Citation] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_ANSWER_STATUSES:
            raise ValueError(f"Unsupported answer status: {self.status}")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 3)
        return payload


@dataclass(frozen=True)
class LLMGroundedAnswerPayload:
    answer: str
    status: str
    confidence: float
    used_citation_ids: list[str]

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_ANSWER_STATUSES:
            raise ValueError(f"Unsupported answer status: {self.status}")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LLMGroundedAnswerPayload":
        answer = str(payload.get("answer", "")).strip()
        status = str(payload.get("status", "")).strip()
        raw_confidence = payload.get("confidence", 0.0)
        used_citation_ids = payload.get("used_citation_ids", [])

        if not isinstance(used_citation_ids, list):
            raise ValueError("used_citation_ids must be a list")

        normalized_ids = [str(item).strip() for item in used_citation_ids if str(item).strip()]
        confidence = max(0.0, min(float(raw_confidence), 1.0))

        return cls(
            answer=answer,
            status=status,
            confidence=confidence,
            used_citation_ids=normalized_ids,
        )
