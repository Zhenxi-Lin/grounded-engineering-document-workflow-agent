from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.extractor import load_crawl_metadata, process_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract readable text from crawled engineering documentation HTML pages."
    )
    parser.add_argument(
        "--metadata-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "metadata.jsonl",
        help="Path to raw crawl metadata JSONL",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Directory containing raw HTML files",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "documents.jsonl",
        help="Path to processed documents JSONL",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional limit for quick debugging; 0 means process all",
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

    records = load_crawl_metadata(args.metadata_path)
    if args.limit > 0:
        records = records[: args.limit]

    processed = process_documents(
        records=records,
        raw_root=args.raw_dir,
        output_path=args.output_path,
    )
    logging.getLogger(__name__).info(
        "Extraction finished: %s documents written to %s",
        len(processed),
        args.output_path,
    )


if __name__ == "__main__":
    main()
