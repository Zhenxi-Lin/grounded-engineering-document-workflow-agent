from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.retrieval.indexer import IndexBuildConfig, build_and_save_indices


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build local retrieval assets from processed chunk data."
    )
    parser.add_argument(
        "--chunks-path",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed" / "chunks.jsonl",
        help="Path to chunk JSONL input",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "index",
        help="Directory for retrieval assets",
    )
    parser.add_argument(
        "--bm25-k1",
        type=float,
        default=1.5,
        help="BM25 k1 parameter",
    )
    parser.add_argument(
        "--bm25-b",
        type=float,
        default=0.75,
        help="BM25 b parameter",
    )
    parser.add_argument(
        "--dense-max-features",
        type=int,
        default=5000,
        help="Maximum TF-IDF features for dense indexing",
    )
    parser.add_argument(
        "--dense-n-components",
        type=int,
        default=256,
        help="Target SVD dimensions for dense indexing",
    )
    parser.add_argument(
        "--dense-ngram-max",
        type=int,
        default=2,
        help="Maximum n-gram size for the dense vectorizer",
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

    config = IndexBuildConfig(
        bm25_k1=args.bm25_k1,
        bm25_b=args.bm25_b,
        dense_max_features=args.dense_max_features,
        dense_n_components=args.dense_n_components,
        dense_ngram_max=args.dense_ngram_max,
    )
    assets = build_and_save_indices(
        chunks_path=args.chunks_path,
        output_dir=args.output_dir,
        config=config,
    )

    logger = logging.getLogger(__name__)
    for name, path in assets.items():
        logger.info("Built %s asset at %s", name, path)


if __name__ == "__main__":
    main()
