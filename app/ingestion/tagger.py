from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LOGGER = logging.getLogger(__name__)

ALLOWED_DOC_TYPES = {
    "getting_started",
    "installation",
    "tutorial",
    "concept",
    "troubleshooting",
    "reference",
    "integration",
    "safety",
}

GENERIC_TOPIC_TITLES = {
    "concepts",
    "getting started",
    "installation",
    "launch",
    "discovery",
    "troubleshooting",
    "reference architecture",
}


@dataclass(frozen=True)
class TaggedField:
    value: str | None
    rule: str


def load_processed_documents(input_path: Path) -> list[dict[str, Any]]:
    LOGGER.info("Loading processed documents from %s", input_path)
    rows: list[dict[str, Any]] = []
    for line in input_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    LOGGER.info("Loaded %s processed documents", len(rows))
    return rows


def tag_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tagged_rows: list[dict[str, Any]] = []
    for document in documents:
        source_tag = infer_source(document.get("url"), document.get("raw_html_path"))
        doc_type_tag = infer_doc_type(
            title=document.get("title"),
            url=document.get("url"),
            page_category=document.get("page_category"),
        )
        version_tag = infer_version(
            url=document.get("url"),
            title=document.get("title"),
            source=document.get("source"),
        )
        topic_tag = infer_topic(
            title=document.get("title"),
            url=document.get("url"),
            page_category=document.get("page_category"),
            source=source_tag.value,
        )

        tagged = dict(document)
        tagged["source"] = source_tag.value
        tagged["doc_type"] = doc_type_tag.value
        tagged["version"] = version_tag.value
        tagged["topic"] = topic_tag.value
        tagged["tagging_debug"] = {
            "source_rule": source_tag.rule,
            "doc_type_rule": doc_type_tag.rule,
            "version_rule": version_tag.rule,
            "topic_rule": topic_tag.rule,
        }
        tagged_rows.append(tagged)

    return tagged_rows


def write_tagged_documents(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(row, ensure_ascii=False) for row in rows]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %s tagged documents to %s", len(rows), output_path)


def infer_source(url: str | None, raw_html_path: str | None) -> TaggedField:
    url_text = (url or "").lower()
    path_text = (raw_html_path or "").lower()

    if "docs.px4.io" in url_text or path_text.startswith("px4_official_docs/"):
        return TaggedField("PX4 official docs", "domain_or_path:px4")
    if "docs.ros.org" in url_text or path_text.startswith("ros_2_official_docs/"):
        return TaggedField("ROS 2 official docs", "domain_or_path:ros2")
    if "moveit.picknik.ai" in url_text or path_text.startswith("moveit_docs/"):
        return TaggedField("MoveIt docs", "domain_or_path:moveit")
    if "nvidia-isaac-ros.github.io" in url_text or path_text.startswith("isaac_ros_docs/"):
        return TaggedField("Isaac ROS docs", "domain_or_path:isaac_ros")
    return TaggedField("Unknown source", "fallback:unknown_source")


def infer_doc_type(title: str | None, url: str | None, page_category: str | None) -> TaggedField:
    title_text = normalize_title_text(title)
    url_text = (url or "").lower()
    category_text = (page_category or "").lower()
    title_url_hint = " ".join(part for part in [title_text.lower(), url_text] if part)

    if any(term in title_url_hint for term in ["safety", "failsafe", "geofence", "arming", "preflight"]):
        return TaggedField("safety", "title_or_url:safety")
    if any(term in title_url_hint for term in ["troubleshoot", "debug", "failure", "faq"]):
        return TaggedField("troubleshooting", "title_or_url:troubleshooting")
    if any(term in title_url_hint for term in ["getting started", "getting_started"]):
        return TaggedField("getting_started", "title_or_url:getting_started")
    if any(term in title_url_hint for term in ["installation", "install ", "install-", "ubuntu-install", "workspace", "building px4", "build ros 2 workspace", "dev_setup", "setup your colcon workspace"]):
        return TaggedField("installation", "title_or_url:installation")
    if any(term in title_url_hint for term in ["concept", "discovery", "overview", "architecture", "planning scene", "motion planning"]):
        return TaggedField("concept", "title_or_url:concept")
    if any(term in title_url_hint for term in ["bridge", "middleware", "offboard", "integration", "controller", "uxrce", "nitros", "docker", "gazebo", "simulation", "sim ", "sim_", "ros 2 user guide"]):
        return TaggedField("integration", "title_or_url:integration")
    if any(term in title_url_hint for term in ["tutorial", "example", "quickstart", "trying it out", "your first project"]):
        return TaggedField("tutorial", "title_or_url:tutorial")

    if any(term in category_text for term in ["safety", "operational_validation"]):
        return TaggedField("safety", "page_category:safety")
    if any(term in category_text for term in ["troubleshooting", "debugging"]):
        return TaggedField("troubleshooting", "page_category:troubleshooting")
    if "getting_started" in category_text:
        return TaggedField("getting_started", "page_category:getting_started")
    if any(term in category_text for term in ["installation", "environment", "setup"]):
        return TaggedField("installation", "page_category:installation")
    if "concept" in category_text:
        return TaggedField("concept", "page_category:concept")
    if any(term in category_text for term in ["integration", "external_integration", "simulation"]):
        return TaggedField("integration", "page_category:integration")
    if "tutorial" in category_text:
        return TaggedField("tutorial", "page_category:tutorial")

    if "tutorials" in url_text:
        return TaggedField("tutorial", "url:tutorials")
    if "concepts" in url_text:
        return TaggedField("concept", "url:concepts")
    if "installation" in url_text:
        return TaggedField("installation", "url:installation")
    if "getting_started" in url_text:
        return TaggedField("getting_started", "url:getting_started")
    return TaggedField("reference", "fallback:reference")


def infer_version(url: str | None, title: str | None, source: str | None) -> TaggedField:
    url_text = url or ""
    title_text = title or ""

    px4_match = re.search(r"/v(\d+\.\d+)/", url_text)
    if px4_match:
        return TaggedField(f"v{px4_match.group(1)}", "url:px4_version")

    ros_match = re.search(r"docs\.ros\.org/en/([^/]+)/", url_text)
    if ros_match:
        return TaggedField(ros_match.group(1), "url:ros_distribution")

    isaac_release_match = re.search(r"/v/(release-[^/]+)/", url_text)
    if isaac_release_match:
        return TaggedField(isaac_release_match.group(1), "url:isaac_release")

    if "moveit.picknik.ai/main/" in url_text:
        return TaggedField("main", "url:moveit_main")

    if "nvidia-isaac-ros.github.io/" in url_text:
        return TaggedField("latest", "url:isaac_latest")

    title_match = re.search(r"\((v[\d.]+)\)", title_text)
    if title_match:
        return TaggedField(title_match.group(1), "title:version_suffix")

    if source == "Isaac ROS docs":
        return TaggedField("latest", "fallback:isaac_latest")
    return TaggedField(None, "fallback:no_version")


def infer_topic(
    title: str | None,
    url: str | None,
    page_category: str | None,
    source: str | None,
) -> TaggedField:
    cleaned_title = normalize_title_text(title)
    if cleaned_title and cleaned_title.lower() not in GENERIC_TOPIC_TITLES:
        return TaggedField(cleaned_title, "title:specific")

    path_topic = infer_topic_from_url(url)
    if path_topic and cleaned_title:
        source_prefix = short_source_prefix(source)
        if cleaned_title.lower() in GENERIC_TOPIC_TITLES:
            return TaggedField(f"{source_prefix} {path_topic}".strip(), "url_path:generic_title")
        return TaggedField(path_topic, "url_path:topic")
    if cleaned_title:
        source_prefix = short_source_prefix(source)
        return TaggedField(f"{source_prefix} {cleaned_title}".strip(), "title:generic_with_source")

    if page_category:
        return TaggedField(page_category.replace("_", " "), "fallback:page_category")
    return TaggedField("unknown", "fallback:unknown")


def infer_topic_from_url(url: str | None) -> str | None:
    if not url:
        return None

    parts = [part for part in urlparse(url).path.strip("/").split("/") if part]
    if not parts:
        return None

    ignored = {
        "en",
        "main",
        "index.html",
        "index",
        "doc",
        "tutorials",
        "concepts",
        "examples",
        "how-to-guides",
        "how_to_guides",
        "repositories_and_packages",
        "getting_started",
    }
    candidates = [part for part in parts if part.lower() not in ignored]
    if not candidates:
        candidates = parts[-2:] if len(parts) >= 2 else parts

    topic = candidates[-1]
    if topic.lower() in {"index", "index.html"}:
        return None
    topic = topic.replace(".html", "")
    topic = topic.replace("_tutorial", "")
    topic = topic.replace("_", " ").replace("-", " ")
    topic = re.sub(r"\s+", " ", topic).strip()
    return normalize_title_text(topic) or None


def normalize_title_text(text: str | None) -> str:
    if not text:
        return ""
    value = text.replace("\u200b", " ").replace("\uf0c1", " ").replace("​", " ")
    value = value.replace("", " ").replace("#", " ")
    value = re.sub(r"\s+", " ", value).strip()
    if " | " in value:
        value = value.split(" | ", 1)[0].strip()
    return value


def short_source_prefix(source: str | None) -> str:
    mapping = {
        "PX4 official docs": "PX4",
        "ROS 2 official docs": "ROS 2",
        "MoveIt docs": "MoveIt",
        "Isaac ROS docs": "Isaac ROS",
    }
    return mapping.get(source or "", "")
