from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.retrieval_service import (
    RetrievalService,
    SUPPORTED_MODES,
    extract_display_score,
    format_result_preview,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run manual retrieval checks over local engineering documentation indexes."
    )
    parser.add_argument(
        "query",
        help="User query to search",
    )
    parser.add_argument(
        "--mode",
        default="hybrid",
        choices=sorted(SUPPORTED_MODES),
        help="Retrieval mode",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of results to return",
    )
    parser.add_argument(
        "--index-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "index",
        help="Directory containing retrieval index assets",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=260,
        help="Maximum characters to show in each text preview",
    )
    parser.add_argument(
        "--log-level",
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    service = RetrievalService.from_index_dir(args.index_dir)
    results = service.search(
        args.query,
        mode=args.mode,
        top_k=args.top_k,
    )

    print(f"Query: {args.query}")
    print(f"Mode: {args.mode}")
    print(f"Top K: {args.top_k}")
    print(f"Results: {len(results)}")
    print()

    if not results:
        print("No results found.")
        return

    for rank, result in enumerate(results, start=1):
        score = extract_display_score(result, args.mode)
        section_path = " > ".join(result.get("section_path", []))
        preview = format_result_preview(result.get("text", ""), max_chars=args.preview_chars)

        print(f"[{rank}] score={score:.4f}")
        print(f"title: {result.get('title')}")
        print(f"source: {result.get('source')}")
        print(f"version: {result.get('version')}")
        print(f"section_path: {section_path}")
        print(f"url: {result.get('url')}")
        print(f"preview: {preview}")
        print("-" * 80)


if __name__ == "__main__":
    main()
