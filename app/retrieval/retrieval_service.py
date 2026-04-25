from __future__ import annotations

import logging
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.dense_retriever import DenseRetriever
from app.retrieval.hybrid_retriever import HybridRetriever


LOGGER = logging.getLogger(__name__)

SUPPORTED_MODES = {"bm25", "dense", "hybrid"}


@dataclass(frozen=True)
class RetrievalAssets:
    bm25_index_path: Path
    dense_index_path: Path


class RetrievalService:
    def __init__(
        self,
        *,
        bm25: BM25Retriever,
        dense: DenseRetriever,
        hybrid: HybridRetriever,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.hybrid = hybrid

    @classmethod
    def from_index_dir(cls, index_dir: Path) -> "RetrievalService":
        assets = resolve_index_assets(index_dir)
        return cls.from_assets(assets)

    @classmethod
    def from_assets(cls, assets: RetrievalAssets) -> "RetrievalService":
        validate_assets(assets)
        bm25 = BM25Retriever.load(assets.bm25_index_path)
        dense = DenseRetriever.load(assets.dense_index_path)
        hybrid = HybridRetriever(bm25=bm25, dense=dense)
        LOGGER.info(
            "Loaded retrieval service assets from %s and %s",
            assets.bm25_index_path,
            assets.dense_index_path,
        )
        return cls(bm25=bm25, dense=dense, hybrid=hybrid)

    def search(
        self,
        query: str,
        *,
        mode: str = "hybrid",
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in SUPPORTED_MODES:
            raise ValueError(f"Unsupported retrieval mode: {mode}")

        query = query.strip()
        if not query:
            raise ValueError("Query cannot be empty")

        LOGGER.info("Running %s retrieval for query: %s", normalized_mode, query)
        if normalized_mode == "bm25":
            return self.bm25.search(query, top_k=top_k, filters=filters)
        if normalized_mode == "dense":
            return self.dense.search(query, top_k=top_k, filters=filters)
        return self.hybrid.search(query, top_k=top_k, filters=filters)


def resolve_index_assets(index_dir: Path) -> RetrievalAssets:
    return RetrievalAssets(
        bm25_index_path=index_dir / "bm25_index.pkl",
        dense_index_path=index_dir / "dense_index.pkl",
    )


def validate_assets(assets: RetrievalAssets) -> None:
    missing = [
        str(path)
        for path in [assets.bm25_index_path, assets.dense_index_path]
        if not path.exists()
    ]
    if missing:
        missing_text = ", ".join(missing)
        raise FileNotFoundError(
            "Missing retrieval index asset(s): "
            f"{missing_text}. Run `python scripts/build_index.py` first."
        )


def format_result_preview(text: str, *, max_chars: int = 260) -> str:
    compact = " ".join(text.split())
    if len(compact) <= max_chars:
        return compact
    return textwrap.shorten(compact, width=max_chars, placeholder="...")


def extract_display_score(result: dict[str, Any], mode: str) -> float:
    normalized_mode = mode.strip().lower()
    if normalized_mode == "bm25":
        return float(result.get("bm25_score", 0.0))
    if normalized_mode == "dense":
        return float(result.get("dense_score", 0.0))
    return float(result.get("final_score", result.get("hybrid_score", 0.0)))


def build_eval_record(
    *,
    query: str,
    retrieval_mode: str,
    rank: int,
    result: dict[str, Any],
    preview_chars: int = 260,
) -> dict[str, Any]:
    return {
        "query": query,
        "retrieval_mode": retrieval_mode,
        "rank": rank,
        "score": extract_display_score(result, retrieval_mode),
        "title": result.get("title"),
        "source": result.get("source"),
        "version": result.get("version"),
        "section_path": result.get("section_path", []),
        "url": result.get("url"),
        "text_preview": format_result_preview(result.get("text", ""), max_chars=preview_chars),
    }
