from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from app.models.answer_models import Citation


ALLOWED_CHECKLIST_STATUSES = {"grounded_checklist", "insufficient_evidence"}


@dataclass(frozen=True)
class GroundedChecklist:
    query: str
    checklist_title: str
    prerequisites: list[str] = field(default_factory=list)
    ordered_steps: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    validation_checks: list[str] = field(default_factory=list)
    status: str = "insufficient_evidence"
    confidence: float = 0.0
    citations: list[Citation] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_CHECKLIST_STATUSES:
            raise ValueError(f"Unsupported checklist status: {self.status}")

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["confidence"] = round(float(self.confidence), 3)
        return payload


@dataclass(frozen=True)
class LLMGroundedChecklistPayload:
    checklist_title: str
    prerequisites: list[str]
    ordered_steps: list[str]
    warnings: list[str]
    validation_checks: list[str]
    status: str
    confidence: float
    used_citation_ids: list[str]

    def __post_init__(self) -> None:
        if self.status not in ALLOWED_CHECKLIST_STATUSES:
            raise ValueError(f"Unsupported checklist status: {self.status}")

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "LLMGroundedChecklistPayload":
        return cls(
            checklist_title=str(payload.get("checklist_title", "")).strip(),
            prerequisites=ensure_string_list(payload.get("prerequisites", []), field_name="prerequisites"),
            ordered_steps=ensure_string_list(payload.get("ordered_steps", []), field_name="ordered_steps"),
            warnings=ensure_string_list(payload.get("warnings", []), field_name="warnings"),
            validation_checks=ensure_string_list(payload.get("validation_checks", []), field_name="validation_checks"),
            status=str(payload.get("status", "")).strip(),
            confidence=max(0.0, min(float(payload.get("confidence", 0.0)), 1.0)),
            used_citation_ids=ensure_string_list(payload.get("used_citation_ids", []), field_name="used_citation_ids"),
        )


def ensure_string_list(value: Any, *, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    return [str(item).strip() for item in value if str(item).strip()]
