from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are a grounded engineering checklist extraction assistant.

You must generate the checklist ONLY from the provided evidence chunks.
Do not use outside knowledge.
Do not guess.
If the evidence does not clearly support a checklist, return status as insufficient_evidence.

Return JSON only with this schema:
{
  "checklist_title": "short technical title",
  "prerequisites": ["item 1", "item 2"],
  "ordered_steps": ["step 1", "step 2"],
  "warnings": ["warning 1"],
  "validation_checks": ["check 1"],
  "status": "grounded_checklist" | "insufficient_evidence",
  "confidence": 0.0 to 1.0,
  "used_citation_ids": ["chunk_id_1", "chunk_id_2"]
}

Rules:
- Use only citation ids from the evidence list.
- Keep the checklist concise, technical, and inspectable.
- Prefer short imperative steps.
- If status is grounded_checklist, include at least one ordered step and at least one valid used_citation_id.
- Do not include unsupported steps or claims.
- If the evidence is too weak or too fragmented, return insufficient_evidence.
"""


def build_grounded_checklist_user_prompt(
    *,
    query: str,
    evidence_results: list[dict[str, Any]],
) -> str:
    evidence_blocks = "\n\n".join(
        format_evidence_block(index=index, result=result)
        for index, result in enumerate(evidence_results, start=1)
    )
    request_text = query.strip() or "Build a grounded engineering checklist from the provided evidence."
    return (
        f"Checklist request:\n{request_text}\n\n"
        "Evidence chunks:\n"
        f"{evidence_blocks}\n\n"
        "Respond with JSON only."
    )


def format_evidence_block(*, index: int, result: dict[str, Any]) -> str:
    section_path = " > ".join(str(item) for item in result.get("section_path", []))
    text = str(result.get("text", "")).strip()
    return (
        f"[Evidence {index}]\n"
        f"chunk_id: {result.get('chunk_id', '')}\n"
        f"title: {result.get('title', '')}\n"
        f"source: {result.get('source', '')}\n"
        f"version: {result.get('version', '')}\n"
        f"doc_type: {result.get('doc_type', '')}\n"
        f"section_path: {section_path}\n"
        f"url: {result.get('url', '')}\n"
        "text:\n"
        f"{text}"
    )
