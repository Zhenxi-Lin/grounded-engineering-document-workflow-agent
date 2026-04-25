from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.crawler import crawl_targets, load_crawl_plan, select_targets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl the first batch of high-value engineering documentation pages."
    )
    parser.add_argument(
        "--plan-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "crawl_plan.json",
        help="Path to crawl_plan.json",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Directory for raw HTML output",
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "metadata.jsonl",
        help="Path to metadata JSONL output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=40,
        help="Maximum number of seed pages to crawl",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=20,
        help="Network timeout per request",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retries for retryable errors",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
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

    plan = load_crawl_plan(args.plan_path)
    targets = select_targets(
        plan=plan,
        output_root=args.raw_dir,
        limit=args.limit,
    )
    records = crawl_targets(
        targets=targets,
        metadata_path=args.metadata_path,
        max_retries=args.max_retries,
        timeout_seconds=args.timeout_seconds,
    )

    success_count = sum(1 for record in records if record["status"] == "success")
    logging.getLogger(__name__).info(
        "Crawl finished: %s/%s pages fetched successfully",
        success_count,
        len(records),
    )


if __name__ == "__main__":
    main()
