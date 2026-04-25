from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.models.answer_models import Citation


ALLOWED_COMPARE_STATUSES = {"grounded_comparison", "insufficient_evidence"}


@dataclass(frozen=True)
class GroundedComparison:
    query: str
    summary: str
    common_points: list[str] = field(default_factory=list)
    differences: list[str] = field(default_factory=list)
    risks_or_implications: list[str] = field(default_factory=list)
    status: str = "insufficient_evidence"
    confidence: float = 0.0
    citations: list[Citation] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_COMPARE_STATUSES:
            raise ValueError(f"Unsupported compare status: {self.status}")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 3)
        return payload


@dataclass(frozen=True)
class LLMGroundedComparisonPayload:
    summary: str
    common_points: list[str]
    differences: list[str]
    risks_or_implications: list[str]
    status: str
    confidence: float
    used_citation_ids: list[str]

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_COMPARE_STATUSES:
            raise ValueError(f"Unsupported compare status: {self.status}")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LLMGroundedComparisonPayload":
        common_points = ensure_string_list(payload.get("common_points", []), field_name="common_points")
        differences = ensure_string_list(payload.get("differences", []), field_name="differences")
        risks_or_implications = ensure_string_list(
            payload.get("risks_or_implications", []),
            field_name="risks_or_implications",
        )
        used_citation_ids = ensure_string_list(
            payload.get("used_citation_ids", []),
            field_name="used_citation_ids",
        )

        return cls(
            summary=str(payload.get("summary", "")).strip(),
            common_points=common_points,
            differences=differences,
            risks_or_implications=risks_or_implications,
            status=str(payload.get("status", "")).strip(),
            confidence=max(0.0, min(float(payload.get("confidence", 0.0)), 1.0)),
            used_citation_ids=[item for item in used_citation_ids if item],
        )


def ensure_string_list(value: Any, *, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [str(item).strip() for item in value if str(item).strip()]
