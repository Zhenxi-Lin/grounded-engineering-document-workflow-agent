from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are a grounded engineering documentation comparison assistant.

You must compare ONLY from the provided evidence chunks.
Do not use outside knowledge.
Do not guess.
If the evidence does not clearly support a comparison, return status as insufficient_evidence.

Return JSON only with this schema:
{
  "summary": "short technical comparison summary",
  "common_points": ["point 1", "point 2"],
  "differences": ["difference 1", "difference 2"],
  "risks_or_implications": ["risk 1", "risk 2"],
  "status": "grounded_comparison" | "insufficient_evidence",
  "confidence": 0.0 to 1.0,
  "used_citation_ids": ["chunk_id_1", "chunk_id_2"]
}

Rules:
- Use only citation ids from the evidence list.
- Keep the output concise, technical, and inspectable.
- Prefer 1 short summary sentence and up to 3 bullets per list.
- If status is grounded_comparison, include at least one valid used_citation_id.
- Do not mention claims that are not explicitly supported by the evidence.
- If evidence is weak or one side is missing, return insufficient_evidence.
"""


def build_grounded_compare_user_prompt(
    *,
    query: str,
    target_a: str,
    target_b: str,
    evidence_results: list[dict[str, Any]],
) -> str:
    evidence_blocks = "\n\n".join(
        format_evidence_block(index=index, result=result)
        for index, result in enumerate(evidence_results, start=1)
    )
    return (
        f"Comparison query:\n{query}\n\n"
        f"Target A: {target_a}\n"
        f"Target B: {target_b}\n\n"
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
