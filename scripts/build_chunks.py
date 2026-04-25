from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.chunker import ChunkConfig, build_chunks, load_tagged_documents, write_chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build retrieval-friendly chunks from tagged engineering documents."
    )
    parser.add_argument(
        "--input-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "tagged_documents.jsonl",
        help="Path to tagged documents JSONL",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "chunks.jsonl",
        help="Path to chunk JSONL output",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional document limit for quick debugging; 0 means process all",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Target maximum characters per chunk",
    )
    parser.add_argument(
        "--min-chars",
        type=int,
        default=350,
        help="Preferred minimum characters per chunk",
    )
    parser.add_argument(
        "--hard-max-chars",
        type=int,
        default=1600,
        help="Hard ceiling used when splitting oversized paragraphs",
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

    documents = load_tagged_documents(args.input_path)
    if args.limit > 0:
        documents = documents[: args.limit]

    config = ChunkConfig(
        max_chars=args.max_chars,
        min_chars=args.min_chars,
        hard_max_chars=args.hard_max_chars,
    )
    chunks = build_chunks(documents, config=config)
    write_chunks(chunks, args.output_path)
    logging.getLogger(__name__).info(
        "Chunk build finished: %s chunks written to %s",
        len(chunks),
        args.output_path,
    )


if __name__ == "__main__":
    main()
