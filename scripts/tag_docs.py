from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.tagger import load_processed_documents, tag_documents, write_tagged_documents


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply transparent rule-based metadata tags to processed engineering documents."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "documents.jsonl",
        help="Path to processed documents JSONL",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "tagged_documents.jsonl",
        help="Path to tagged documents JSONL",
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

    documents = load_processed_documents(args.input_path)
    if args.limit > 0:
        documents = documents[: args.limit]

    tagged = tag_documents(documents)
    write_tagged_documents(tagged, args.output_path)
    logging.getLogger(__name__).info(
        "Tagging finished: %s documents written to %s",
        len(tagged),
        args.output_path,
    )


if __name__ == "__main__":
    main()
