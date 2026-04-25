from __future__ import annotations

from typing import Any


SYSTEM_PROMPT = """You are a grounded engineering documentation QA assistant.

You must answer ONLY from the provided evidence chunks.
Do not use outside knowledge.
Do not guess.
If the evidence does not clearly support an answer, return status as insufficient_evidence.

Return JSON only with this schema:
{
  "answer": "short technical answer",
  "status": "grounded_answer" | "insufficient_evidence",
  "confidence": 0.0 to 1.0,
  "used_citation_ids": ["chunk_id_1", "chunk_id_2"]
}

Rules:
- Keep the answer concise, technical, and inspectable.
- Use only citation ids from the evidence list.
- If status is grounded_answer, include at least one used_citation_id.
- Do not mention information that is not explicitly supported by the evidence.
- Prefer 1-3 short sentences.
"""


def build_grounded_qa_user_prompt(
    *,
    query: str,
    evidence_results: list[dict[str, Any]],
) -> str:
    evidence_blocks = "\n\n".join(
        format_evidence_block(index=index, result=result)
        for index, result in enumerate(evidence_results, start=1)
    )
    return (
        f"Query:\n{query}\n\n"
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
