from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LOGGER = logging.getLogger(__name__)

HEADER_TAGS = {"h1", "h2", "h3", "h4"}
BLOCK_TAGS = {
    "p",
    "div",
    "section",
    "article",
    "main",
    "ul",
    "ol",
    "pre",
    "table",
    "tr",
    "blockquote",
    "details",
    "summary",
    "dl",
    "dt",
    "dd",
    "br",
}
SKIP_TAGS = {"script", "style", "noscript", "svg", "iframe", "canvas", "nav", "aside", "footer"}
NOISE_KEYWORDS = {
    "toc",
    "tableofcontents",
    "breadcrumb",
    "search",
    "skip",
    "prev-next",
    "pagination",
    "edit",
    "social",
    "theme-switch",
    "version-switcher",
    "versions",
    "language",
    "translation",
    "outline",
    "page-toc",
    "toc-nav",
    "related",
}
PREFERRED_CLASS_MARKERS = [
    "theme-doc-markdown",
    "vp-doc",
    "bd-article",
    "rst-content",
    "wy-nav-content",
    "md-content",
    "content-container",
]
HEADER_MARKER_RE = re.compile(r"^\[\[HEADER:(h[1-4])\]\]\s*")
MULTISPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ExtractionResult:
    title: str | None
    cleaned_text: str
    section_headers: list[str]
    extractor_mode: str


@dataclass(frozen=True)
class RawDocumentRecord:
    source_name: str
    url: str
    raw_html_path: str
    page_category: str | None
    title: str | None


@dataclass
class _NodeState:
    tag: str
    skip: bool
    capture: bool


class MainContentHTMLParser(HTMLParser):
    def __init__(self, extractor_mode: str) -> None:
        super().__init__(convert_charrefs=True)
        self.extractor_mode = extractor_mode
        self.stack: list[_NodeState] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {key: (value or "") for key, value in attrs}
        classes = tokenize_attr(attrs_map.get("class", ""))
        ids = tokenize_attr(attrs_map.get("id", ""))

        parent_skip = self.stack[-1].skip if self.stack else False
        parent_capture = self.stack[-1].capture if self.stack else False

        skip = parent_skip or should_skip_element(tag, classes, ids)
        capture = False
        if not skip:
            capture = parent_capture or is_capture_start(
                tag=tag,
                classes=classes,
                ids=ids,
                extractor_mode=self.extractor_mode,
            )

        self.stack.append(_NodeState(tag=tag, skip=skip, capture=capture))

        if not capture or skip:
            return

        if tag in HEADER_TAGS:
            self.parts.append(f"\n[[HEADER:{tag}]] ")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "br" and self._is_currently_capturing():
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return

        match_index = None
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                match_index = index
                break

        if match_index is None:
            return

        node = self.stack[match_index]
        del self.stack[match_index:]
        if not node.capture or node.skip:
            return

        if tag in HEADER_TAGS or tag in BLOCK_TAGS or tag == "li":
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not data or not self._is_currently_capturing():
            return
        self.parts.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._is_currently_capturing():
            self.parts.append(unescape(f"&{name};"))

    def handle_charref(self, name: str) -> None:
        if self._is_currently_capturing():
            self.parts.append(unescape(f"&#{name};"))

    def get_text(self) -> str:
        return "".join(self.parts)

    def _is_currently_capturing(self) -> bool:
        return bool(self.stack) and self.stack[-1].capture and not self.stack[-1].skip


def load_crawl_metadata(metadata_path: Path) -> list[RawDocumentRecord]:
    LOGGER.info("Loading crawl metadata from %s", metadata_path)
    records: list[RawDocumentRecord] = []
    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if data.get("status") != "success" or not data.get("raw_html_path"):
            continue
        records.append(
            RawDocumentRecord(
                source_name=data["source_name"],
                url=data["final_url"] or data["url"],
                raw_html_path=data["raw_html_path"],
                page_category=data.get("page_category"),
                title=data.get("title"),
            )
        )
    LOGGER.info("Loaded %s successful raw document records", len(records))
    return records


def extract_document(html_text: str, fallback_title: str | None = None) -> ExtractionResult:
    extractor_mode = detect_extractor_mode(html_text)
    parser = MainContentHTMLParser(extractor_mode=extractor_mode)
    parser.feed(html_text)
    parser.close()

    html_title = extract_html_title(html_text)
    cleaned_text, section_headers, inferred_title = clean_extracted_text(parser.get_text())
    title = inferred_title or normalize_title(html_title) or normalize_title(fallback_title)

    if title and (not section_headers or section_headers[0] != title):
        section_headers = [title] + [header for header in section_headers if header != title]
        if not cleaned_text.startswith("# "):
            cleaned_text = f"# {title}\n\n{cleaned_text}".strip()

    return ExtractionResult(
        title=title,
        cleaned_text=cleaned_text,
        section_headers=section_headers,
        extractor_mode=extractor_mode,
    )


def process_documents(
    records: list[RawDocumentRecord],
    raw_root: Path,
    output_path: Path,
) -> list[dict[str, Any]]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed: list[dict[str, Any]] = []

    for index, record in enumerate(records, start=1):
        raw_path = raw_root / record.raw_html_path
        LOGGER.info("[%s/%s] Extracting %s", index, len(records), raw_path)
        if not raw_path.exists():
            LOGGER.warning("Raw HTML file missing: %s", raw_path)
            continue

        html_text = raw_path.read_text(encoding="utf-8", errors="ignore")
        extracted = extract_document(html_text, fallback_title=record.title)
        document = {
            "source": record.source_name,
            "url": record.url,
            "title": extracted.title,
            "cleaned_text": extracted.cleaned_text,
            "section_headers": extracted.section_headers,
            "doc_type": infer_doc_type(record.url, extracted.title, record.page_category),
            "version": infer_version(record.url, record.title, record.source_name),
            "topic": infer_topic(extracted.title, record.url, record.page_category),
            "page_category": record.page_category,
            "raw_html_path": record.raw_html_path,
            "extractor_mode": extracted.extractor_mode,
        }
        processed.append(document)

    write_jsonl(processed, output_path)
    LOGGER.info("Wrote %s processed documents to %s", len(processed), output_path)
    return processed


def write_jsonl(records: list[dict[str, Any]], output_path: Path) -> None:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def detect_extractor_mode(html_text: str) -> str:
    lowered = html_text.lower()
    for marker in PREFERRED_CLASS_MARKERS:
        if marker in lowered:
            return marker
    if "<article" in lowered:
        return "article"
    if "<main" in lowered:
        return "main"
    return "body"


def should_skip_element(tag: str, classes: set[str], ids: set[str]) -> bool:
    if tag in SKIP_TAGS:
        return True

    tokens = classes | ids
    return any(any(keyword in token for keyword in NOISE_KEYWORDS) for token in tokens)


def is_capture_start(tag: str, classes: set[str], ids: set[str], extractor_mode: str) -> bool:
    if extractor_mode == "article":
        return tag == "article"
    if extractor_mode == "main":
        return tag == "main"
    if extractor_mode == "body":
        return tag == "body"

    tokens = classes | ids
    if extractor_mode in {"vp-doc", "content-container"}:
        return any(extractor_mode in token for token in tokens)
    if extractor_mode in {"theme-doc-markdown", "bd-article", "rst-content", "wy-nav-content", "md-content"}:
        return any(extractor_mode in token for token in tokens)
    return False


def tokenize_attr(value: str) -> set[str]:
    raw_tokens = [token for token in value.lower().split() if token]
    derived_tokens: set[str] = set(raw_tokens)
    for token in raw_tokens:
        derived_tokens.update(part for part in re.split(r"[_:/.]+", token) if part)
    return derived_tokens


def extract_html_title(html_text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html_text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = normalize_inline_text(match.group(1))
    return title or None


def clean_extracted_text(raw_text: str) -> tuple[str, list[str], str | None]:
    lines = raw_text.splitlines()
    cleaned_lines: list[str] = []
    section_headers: list[str] = []
    title: str | None = None
    pending_header_level: int | None = None
    seen_main_header = False
    previous_normalized_line: str | None = None

    for raw_line in lines:
        line = (
            raw_line.replace("\xa0", " ")
            .replace("", " ")
            .replace("\uf0c1", " ")
            .replace("#", " # ")
        )
        line = normalize_inline_text(line)
        if not line:
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            continue

        header_match = HEADER_MARKER_RE.match(line)
        if header_match:
            pending_header_level = int(header_match.group(1)[1])
            line = HEADER_MARKER_RE.sub("", line).strip()
            if not line:
                continue

        if pending_header_level is not None:
            header_level = pending_header_level
            header_text = clean_header_text(line)
            pending_header_level = None
            if not header_text or is_noise_line(header_text):
                continue

            if not title:
                title = header_text
            if header_text not in section_headers:
                section_headers.append(header_text)

            cleaned_lines.append(f"{'#' * header_level} {header_text}".strip())
            previous_normalized_line = header_text.lower()
            seen_main_header = True
            continue

        if is_noise_line(line):
            continue

        if not seen_main_header:
            continue

        normalized_line = line.lower()
        if normalized_line == previous_normalized_line:
            continue

        cleaned_lines.append(line)
        previous_normalized_line = normalized_line

    cleaned_text = finalize_cleaned_text(cleaned_lines)
    section_headers = dedupe_preserve_order(section_headers)
    return cleaned_text, section_headers, title


def clean_header_text(text: str) -> str:
    text = normalize_inline_text(text.replace("\uf0c1", " "))
    text = text.removesuffix(" #").strip()
    return text


def normalize_inline_text(text: str) -> str:
    text = unescape(text)
    text = MULTISPACE_RE.sub(" ", text)
    return text.strip()


def finalize_cleaned_text(lines: list[str]) -> str:
    compacted: list[str] = []
    blank_pending = False

    for line in lines:
        if not line:
            blank_pending = True
            continue
        if blank_pending and compacted:
            compacted.append("")
        compacted.append(line)
        blank_pending = False

    return "\n".join(compacted).strip()


def is_noise_line(line: str) -> bool:
    lowered = line.lower().strip()
    if not lowered:
        return True

    exact_noise = {
        "on this page",
        "contents",
        "main navigation",
        "sidebar navigation",
        "navigation",
        "search",
        "skip to content",
        "skip to main content",
        "return to top",
        "back to top",
        "previous",
        "next",
        "home",
        "read the docs",
        "edit on github",
        "open issue",
        "show source",
        "table of contents",
        "breadcrumb",
    }
    if lowered in exact_noise:
        return True

    prefix_noise = (
        "toggle navigation",
        "search docs",
        "view page source",
        "copyright",
        "last updated",
    )
    if any(lowered.startswith(prefix) for prefix in prefix_noise):
        return True

    if "»" in line and len(line) < 120:
        return True

    if re.fullmatch(r"[-#>*\s]+", line):
        return True

    return False


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def normalize_title(title: str | None) -> str | None:
    if not title:
        return None
    value = title
    if " | " in value:
        value = value.split(" | ", 1)[0]
    if " — " in value:
        value = value.split(" — ", 1)[0]
    value = re.sub(r"\s+\(v[\d.]+\)$", "", value).strip()
    value = re.sub(r"\s+documentation$", "", value, flags=re.IGNORECASE).strip()
    return value or None


def infer_doc_type(url: str, title: str | None, page_category: str | None) -> str:
    hint = " ".join(filter(None, [url.lower(), (title or "").lower(), (page_category or "").lower()]))
    if any(keyword in hint for keyword in ["safety", "failsafe"]):
        return "safety"
    if any(keyword in hint for keyword in ["troubleshoot", "debug", "failure", "faq"]):
        return "troubleshooting"
    if any(keyword in hint for keyword in ["tutorial", "quickstart", "example", "walkthrough", "getting_started"]):
        return "tutorial"
    if any(keyword in hint for keyword in ["install", "installation", "setup", "workspace", "build"]):
        return "setup"
    if any(keyword in hint for keyword in ["concept", "overview", "architecture"]):
        return "concept"
    if any(keyword in hint for keyword in ["integration", "bridge", "middleware", "offboard", "controller", "docker", "sim"]):
        return "integration"
    return "reference"


def infer_version(url: str, title: str | None, source_name: str) -> str | None:
    px4_match = re.search(r"/v(\d+\.\d+)/", url)
    if px4_match:
        return f"v{px4_match.group(1)}"

    ros_match = re.search(r"docs\.ros\.org/en/([^/]+)/", url)
    if ros_match:
        return ros_match.group(1)

    isaac_match = re.search(r"/v/(release-[^/]+)/", url)
    if isaac_match:
        return isaac_match.group(1)

    if "moveit.picknik.ai/main/" in url:
        return "main"
    if "nvidia-isaac-ros.github.io/" in url:
        return "latest"

    if title:
        title_match = re.search(r"\((v[\d.]+)\)", title)
        if title_match:
            return title_match.group(1)

    if "Isaac ROS" in source_name:
        return "latest"
    return None


def infer_topic(title: str | None, url: str, page_category: str | None) -> str:
    normalized_title = normalize_title(title)
    if normalized_title:
        return normalized_title

    path = urlparse(url).path.strip("/")
    if path:
        return path.split("/")[-1].replace(".html", "").replace("_", " ").replace("-", " ").strip()

    return page_category or "unknown"
