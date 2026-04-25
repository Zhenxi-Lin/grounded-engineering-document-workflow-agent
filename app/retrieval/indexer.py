from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


@dataclass(frozen=True)
class IndexBuildConfig:
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    dense_max_features: int = 5000
    dense_n_components: int = 256
    dense_ngram_max: int = 2


def load_chunks(chunks_path: Path) -> list[dict[str, Any]]:
    LOGGER.info("Loading chunks from %s", chunks_path)
    rows: list[dict[str, Any]] = []
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    LOGGER.info("Loaded %s chunks", len(rows))
    return rows


def tokenize_text(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def match_filters(chunk: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    if not filters:
        return True

    for key, expected in filters.items():
        actual = chunk.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        else:
            if actual != expected:
                return False
    return True


def prepare_result(
    chunk: dict[str, Any],
    score: float,
    score_key: str = "score",
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = dict(chunk)
    result[score_key] = float(score)
    if extra_fields:
        result.update(extra_fields)
    return result


def ensure_output_dir(output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_metadata_jsonl(chunks: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    LOGGER.info("Wrote chunk metadata to %s", output_path)


def write_manifest(
    output_path: Path,
    *,
    chunk_count: int,
    config: IndexBuildConfig,
    bm25_path: Path,
    dense_path: Path,
    metadata_path: Path,
) -> None:
    manifest = {
        "chunk_count": chunk_count,
        "config": asdict(config),
        "assets": {
            "bm25_index": bm25_path.name,
            "dense_index": dense_path.name,
            "metadata": metadata_path.name,
        },
    }
    output_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    LOGGER.info("Wrote index manifest to %s", output_path)


def build_and_save_indices(
    *,
    chunks_path: Path,
    output_dir: Path,
    config: IndexBuildConfig | None = None,
) -> dict[str, Path]:
    from app.retrieval.bm25_retriever import BM25Config, BM25Retriever
    from app.retrieval.dense_retriever import DenseConfig, DenseRetriever

    config = config or IndexBuildConfig()
    output_dir = ensure_output_dir(output_dir)

    chunks = load_chunks(chunks_path)
    if not chunks:
        raise ValueError(f"No chunks found in {chunks_path}")

    metadata_path = output_dir / "metadata.jsonl"
    bm25_path = output_dir / "bm25_index.pkl"
    dense_path = output_dir / "dense_index.pkl"
    manifest_path = output_dir / "manifest.json"

    write_metadata_jsonl(chunks, metadata_path)

    bm25 = BM25Retriever.build(
        chunks,
        config=BM25Config(k1=config.bm25_k1, b=config.bm25_b),
    )
    bm25.save(bm25_path)

    dense = DenseRetriever.build(
        chunks,
        config=DenseConfig(
            max_features=config.dense_max_features,
            n_components=config.dense_n_components,
            ngram_max=config.dense_ngram_max,
        ),
    )
    dense.save(dense_path)

    write_manifest(
        manifest_path,
        chunk_count=len(chunks),
        config=config,
        bm25_path=bm25_path,
        dense_path=dense_path,
        metadata_path=metadata_path,
    )

    return {
        "metadata": metadata_path,
        "bm25": bm25_path,
        "dense": dense_path,
        "manifest": manifest_path,
    }
