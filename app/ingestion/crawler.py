from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


LOGGER = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "GroundedEngineeringDocCrawler/0.1"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_MAX_RETRIES = 3
DEFAULT_LIMIT = 40
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


@dataclass(frozen=True)
class CrawlTarget:
    source_name: str
    source_slug: str
    source_priority: str
    base_url: str
    page_category: str
    category_priority: str
    path: str
    url: str
    local_html_path: Path


@dataclass(frozen=True)
class FetchResult:
    ok: bool
    status_code: int | None
    final_url: str
    content_type: str | None
    html_bytes: bytes | None
    error: str | None


def load_crawl_plan(plan_path: Path) -> dict[str, Any]:
    LOGGER.info("Loading crawl plan from %s", plan_path)
    data = json.loads(plan_path.read_text(encoding="utf-8"))
    if "sources" not in data or not isinstance(data["sources"], list):
        raise ValueError("crawl_plan.json is missing a valid 'sources' list")
    return data


def select_targets(
    plan: dict[str, Any],
    output_root: Path,
    limit: int = DEFAULT_LIMIT,
) -> list[CrawlTarget]:
    targets: list[CrawlTarget] = []
    seen_urls: set[str] = set()
    global_rules = plan.get("global_exclude_rules", [])

    for source in plan["sources"]:
        source_slug = slugify_text(source["source_name"])
        source_dir = output_root / source_slug
        source_rules = list(global_rules) + list(source.get("exclude_rules", []))

        for raw_path in source.get("example_paths", []):
            path = normalize_doc_path(raw_path)
            if is_excluded(path, source_rules):
                LOGGER.debug("Skipping excluded path: %s %s", source["source_name"], path)
                continue

            category_name, category_priority = classify_path(
                path,
                source.get("page_categories", []),
            )
            url = urljoin(source["base_url"], path.lstrip("/"))
            if url in seen_urls:
                continue

            local_html_path = source_dir / build_html_filename(path)
            targets.append(
                CrawlTarget(
                    source_name=source["source_name"],
                    source_slug=source_slug,
                    source_priority=source["priority_level"],
                    base_url=source["base_url"],
                    page_category=category_name,
                    category_priority=category_priority,
                    path=path,
                    url=url,
                    local_html_path=local_html_path,
                )
            )
            seen_urls.add(url)

            if len(targets) >= limit:
                LOGGER.info("Selected %s targets (limit reached)", len(targets))
                return targets

    LOGGER.info("Selected %s targets from crawl plan", len(targets))
    return targets


def crawl_targets(
    targets: list[CrawlTarget],
    metadata_path: Path,
    max_retries: int = DEFAULT_MAX_RETRIES,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    user_agent: str = DEFAULT_USER_AGENT,
) -> list[dict[str, Any]]:
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    LOGGER.info("Starting crawl for %s targets", len(targets))
    for index, target in enumerate(targets, start=1):
        LOGGER.info("[%s/%s] Fetching %s", index, len(targets), target.url)
        result = fetch_html(
            url=target.url,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        record = build_metadata_record(target, result)

        if result.ok and result.html_bytes is not None:
            target.local_html_path.parent.mkdir(parents=True, exist_ok=True)
            target.local_html_path.write_bytes(result.html_bytes)
            record["raw_html_path"] = to_posix_relative_path(target.local_html_path, metadata_path.parent)
            record["title"] = extract_title(result.html_bytes)
            LOGGER.info("Saved HTML to %s", target.local_html_path)
        else:
            record["raw_html_path"] = None
            record["title"] = None
            LOGGER.warning("Failed to fetch %s: %s", target.url, result.error)

        records.append(record)

    write_metadata_jsonl(records, metadata_path)
    LOGGER.info("Wrote metadata to %s", metadata_path)
    return records


def fetch_html(
    url: str,
    max_retries: int,
    timeout_seconds: int,
    user_agent: str,
) -> FetchResult:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    for attempt in range(1, max_retries + 1):
        try:
            with urlopen(request, timeout=timeout_seconds) as response:
                status_code = getattr(response, "status", 200)
                final_url = response.geturl()
                content_type = response.headers.get("Content-Type")
                body = response.read()

                if content_type and "html" not in content_type.lower():
                    return FetchResult(
                        ok=False,
                        status_code=status_code,
                        final_url=final_url,
                        content_type=content_type,
                        html_bytes=None,
                        error=f"unexpected content type: {content_type}",
                    )

                return FetchResult(
                    ok=True,
                    status_code=status_code,
                    final_url=final_url,
                    content_type=content_type,
                    html_bytes=body,
                    error=None,
                )
        except HTTPError as error:
            if error.code in RETRYABLE_STATUS_CODES and attempt < max_retries:
                sleep_seconds = attempt
                LOGGER.warning(
                    "HTTP %s for %s on attempt %s/%s, retrying in %ss",
                    error.code,
                    url,
                    attempt,
                    max_retries,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
                continue

            return FetchResult(
                ok=False,
                status_code=error.code,
                final_url=url,
                content_type=error.headers.get("Content-Type") if error.headers else None,
                html_bytes=None,
                error=f"HTTPError {error.code}: {error.reason}",
            )
        except URLError as error:
            if attempt < max_retries:
                sleep_seconds = attempt
                LOGGER.warning(
                    "URLError for %s on attempt %s/%s, retrying in %ss: %s",
                    url,
                    attempt,
                    max_retries,
                    sleep_seconds,
                    error,
                )
                time.sleep(sleep_seconds)
                continue

            return FetchResult(
                ok=False,
                status_code=None,
                final_url=url,
                content_type=None,
                html_bytes=None,
                error=f"URLError: {error}",
            )
        except TimeoutError as error:
            if attempt < max_retries:
                sleep_seconds = attempt
                LOGGER.warning(
                    "Timeout for %s on attempt %s/%s, retrying in %ss",
                    url,
                    attempt,
                    max_retries,
                    sleep_seconds,
                )
                time.sleep(sleep_seconds)
                continue

            return FetchResult(
                ok=False,
                status_code=None,
                final_url=url,
                content_type=None,
                html_bytes=None,
                error=f"TimeoutError: {error}",
            )

    return FetchResult(
        ok=False,
        status_code=None,
        final_url=url,
        content_type=None,
        html_bytes=None,
        error="unknown fetch failure",
    )


def build_metadata_record(target: CrawlTarget, result: FetchResult) -> dict[str, Any]:
    return {
        "source_name": target.source_name,
        "source_slug": target.source_slug,
        "source_priority": target.source_priority,
        "page_category": target.page_category,
        "category_priority": target.category_priority,
        "base_url": target.base_url,
        "path": target.path,
        "url": target.url,
        "final_url": result.final_url,
        "status": "success" if result.ok else "failed",
        "status_code": result.status_code,
        "content_type": result.content_type,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "error": result.error,
    }


def write_metadata_jsonl(records: list[dict[str, Any]], metadata_path: Path) -> None:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    metadata_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def classify_path(path: str, page_categories: list[dict[str, Any]]) -> tuple[str, str]:
    best_name = "uncategorized"
    best_priority = "P9"
    best_score = -1

    for category in page_categories:
        for pattern in category.get("include_patterns", []):
            if path == pattern or path.startswith(pattern) or pattern in path:
                score = len(pattern)
                if score > best_score:
                    best_name = category["category_name"]
                    best_priority = category["priority"]
                    best_score = score

    return best_name, best_priority


def is_excluded(path: str, rules: list[dict[str, str]]) -> bool:
    for rule in rules:
        rule_type = rule.get("rule_type")
        pattern = rule.get("pattern", "")
        if rule_type == "substring" and pattern in path:
            return True
        if rule_type == "regex" and re.search(pattern, path):
            return True
    return False


def normalize_doc_path(path: str) -> str:
    if not path:
        raise ValueError("empty document path in crawl plan")
    return path if path.startswith("/") else f"/{path}"


def build_html_filename(path: str) -> str:
    parsed = urlparse(path)
    clean_path = parsed.path.strip("/")
    parts = [part for part in clean_path.split("/") if part]

    if not parts:
        parts = ["index"]
    elif parsed.path.endswith("/"):
        parts.append("index")

    normalized_parts: list[str] = []
    for part in parts:
        stem = part[:-5] if part.lower().endswith(".html") else part
        normalized_parts.append(slugify_text(stem))

    return "__".join(normalized_parts) + ".html"


def slugify_text(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return normalized.strip("_") or "item"


def extract_title(html_bytes: bytes) -> str | None:
    text = html_bytes.decode("utf-8", errors="ignore")
    match = re.search(r"<title[^>]*>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    raw_title = re.sub(r"\s+", " ", match.group(1)).strip()
    return unescape(raw_title) or None


def to_posix_relative_path(path: Path, relative_to: Path) -> str:
    return path.relative_to(relative_to).as_posix()
