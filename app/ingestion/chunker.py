from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class ChunkConfig:
    max_chars: int = 1200
    min_chars: int = 350
    hard_max_chars: int = 1600


@dataclass(frozen=True)
class Section:
    section_path: list[str]
    heading_level: int
    body: str


def load_tagged_documents(input_path: Path) -> list[dict[str, Any]]:
    LOGGER.info("Loading tagged documents from %s", input_path)
    rows: list[dict[str, Any]] = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    LOGGER.info("Loaded %s tagged documents", len(rows))
    return rows


def build_chunks(
    documents: list[dict[str, Any]],
    config: ChunkConfig | None = None,
) -> list[dict[str, Any]]:
    config = config or ChunkConfig()
    chunks: list[dict[str, Any]] = []

    for document in documents:
        document_chunks = chunk_document(document, config)
        chunks.extend(document_chunks)

    LOGGER.info("Built %s chunks from %s documents", len(chunks), len(documents))
    return chunks


def chunk_document(document: dict[str, Any], config: ChunkConfig) -> list[dict[str, Any]]:
    title = normalize_text(document.get("title"))
    cleaned_text = document.get("cleaned_text", "")
    if not cleaned_text.strip():
        return []

    sections = parse_sections(cleaned_text, fallback_title=title or "Untitled")
    chunk_rows: list[dict[str, Any]] = []
    chunk_counter = 0

    for section in sections:
        section_chunks = chunk_section(section, title=title or "Untitled", config=config)
        for chunk_text in section_chunks:
            chunk_id = build_chunk_id(document, chunk_counter)
            chunk_rows.append(
                {
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "title": title,
                    "source": document.get("source"),
                    "doc_type": document.get("doc_type"),
                    "version": document.get("version"),
                    "section_path": section.section_path,
                    "url": document.get("url"),
                    "topic": document.get("topic"),
                    "page_category": document.get("page_category"),
                    "chunk_index": chunk_counter,
                }
            )
            chunk_counter += 1

    return chunk_rows


def parse_sections(cleaned_text: str, fallback_title: str) -> list[Section]:
    lines = cleaned_text.splitlines()
    sections: list[Section] = []
    heading_stack: list[str] = []
    current_level = 1
    current_body_lines: list[str] = []

    def flush_current_section() -> None:
        body = finalize_text(current_body_lines)
        if not body:
            return
        section_path = heading_stack[:] if heading_stack else [fallback_title]
        sections.append(
            Section(
                section_path=section_path,
                heading_level=current_level,
                body=body,
            )
        )

    for raw_line in lines:
        line = raw_line.rstrip()
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush_current_section()
            current_body_lines = []

            level = len(heading_match.group(1))
            heading_text = normalize_text(heading_match.group(2))
            heading_stack = heading_stack[: max(level - 1, 0)]
            heading_stack.append(heading_text)
            current_level = level
            continue

        current_body_lines.append(line)

    flush_current_section()

    if not sections:
        body = finalize_text(lines)
        if body:
            sections.append(
                Section(
                    section_path=[fallback_title],
                    heading_level=1,
                    body=body,
                )
            )
    return sections


def chunk_section(section: Section, title: str, config: ChunkConfig) -> list[str]:
    paragraphs = filter_redundant_paragraphs(
        split_into_paragraphs(section.body),
        title=title,
        section_path=section.section_path,
    )
    if not paragraphs:
        return []

    chunk_texts: list[str] = []
    current_parts: list[str] = []

    for paragraph in paragraphs:
        paragraph_chunks = split_oversized_paragraph(paragraph, config.hard_max_chars)
        for piece in paragraph_chunks:
            candidate_parts = current_parts + [piece]
            candidate_text = render_chunk_text(title, section.section_path, candidate_parts)

            if current_parts and len(candidate_text) > config.max_chars:
                chunk_texts.append(render_chunk_text(title, section.section_path, current_parts))
                current_parts = [piece]
                continue

            current_parts = candidate_parts

    if current_parts:
        current_text = render_chunk_text(title, section.section_path, current_parts)
        if chunk_texts and len(current_text) < config.min_chars:
            merged = merge_chunk_texts(chunk_texts.pop(), current_text)
            if len(merged) <= config.hard_max_chars:
                chunk_texts.append(merged)
            else:
                chunk_texts.append(render_chunk_text(title, section.section_path, current_parts))
        else:
            chunk_texts.append(current_text)

    return [text for text in chunk_texts if text.strip()]


def filter_redundant_paragraphs(
    paragraphs: list[str],
    title: str,
    section_path: list[str],
) -> list[str]:
    heading_texts = {normalize_heading_text(title).lower()}
    heading_texts.update(normalize_heading_text(item).lower() for item in section_path)

    filtered: list[str] = []
    for paragraph in paragraphs:
        normalized = normalize_heading_text(paragraph).lower()
        if normalized in heading_texts:
            continue
        filtered.append(paragraph)
    return filtered


def render_chunk_text(title: str, section_path: list[str], paragraphs: list[str]) -> str:
    lines: list[str] = [f"# {title}"]

    for depth, heading in enumerate(section_path[1:], start=2):
        lines.append(f"{'#' * min(depth, 6)} {heading}")

    if paragraphs:
        lines.append("")
        lines.append("\n\n".join(paragraphs).strip())

    return "\n".join(lines).strip()


def merge_chunk_texts(previous_text: str, current_text: str) -> str:
    previous_lines = previous_text.splitlines()
    current_lines = current_text.splitlines()

    while current_lines and current_lines[0].startswith("#"):
        current_lines.pop(0)
    while current_lines and not current_lines[0].strip():
        current_lines.pop(0)

    merged_lines = previous_lines + [""] + current_lines
    return "\n".join(merged_lines).strip()


def split_into_paragraphs(text: str) -> list[str]:
    raw_parts = re.split(r"\n\s*\n", text)
    return [normalize_paragraph(part) for part in raw_parts if normalize_paragraph(part)]


def split_oversized_paragraph(paragraph: str, hard_max_chars: int) -> list[str]:
    if len(paragraph) <= hard_max_chars:
        return [paragraph]

    lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
    if len(lines) > 1:
        pieces: list[str] = []
        current_lines: list[str] = []
        for line in lines:
            candidate = "\n".join(current_lines + [line]).strip()
            if current_lines and len(candidate) > hard_max_chars:
                pieces.append("\n".join(current_lines).strip())
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            pieces.append("\n".join(current_lines).strip())
        return pieces

    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    pieces = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if current and len(candidate) > hard_max_chars:
            pieces.append(current.strip())
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current.strip())

    if not pieces:
        return [paragraph[i : i + hard_max_chars].strip() for i in range(0, len(paragraph), hard_max_chars)]
    return pieces


def normalize_paragraph(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    cleaned_lines: list[str] = []
    for line in lines:
        normalized = normalize_text(line)
        if normalized:
            cleaned_lines.append(normalized)
    return "\n".join(cleaned_lines).strip()


def finalize_text(lines: list[str]) -> str:
    text = "\n".join(lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    value = str(text)
    value = value.replace("\u200b", " ").replace("​", " ").replace("\uf0c1", " ").replace("", " ")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def normalize_heading_text(text: Any) -> str:
    value = normalize_text(text)
    value = re.sub(r"^#{1,6}\s+", "", value).strip()
    return value


def build_chunk_id(document: dict[str, Any], chunk_index: int) -> str:
    source_slug = slugify(document.get("source") or "unknown_source")
    title_slug = slugify(document.get("title") or document.get("topic") or "untitled")
    return f"{source_slug}:{title_slug}:{chunk_index:04d}"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "item"


def write_chunks(chunks: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %s chunks to %s", len(chunks), output_path)
