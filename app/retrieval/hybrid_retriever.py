from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.dense_retriever import DenseRetriever
from app.retrieval.query_router import infer_query_route
from app.retrieval.ranking import rerank_results


LOGGER = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(
        self,
        *,
        bm25: BM25Retriever,
        dense: DenseRetriever,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
        rrf_k: int = 60,
    ) -> None:
        self.bm25 = bm25
        self.dense = dense
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self.rrf_k = rrf_k

    @classmethod
    def from_paths(
        cls,
        *,
        bm25_index_path: Path,
        dense_index_path: Path,
        bm25_weight: float = 1.0,
        dense_weight: float = 1.0,
        rrf_k: int = 60,
    ) -> "HybridRetriever":
        return cls(
            bm25=BM25Retriever.load(bm25_index_path),
            dense=DenseRetriever.load(dense_index_path),
            bm25_weight=bm25_weight,
            dense_weight=dense_weight,
            rrf_k=rrf_k,
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
        candidate_k: int | None = None,
    ) -> list[dict[str, Any]]:
        candidate_k = candidate_k or max(top_k * 4, 20)
        route = infer_query_route(query)

        bm25_results = self.bm25.search(query, top_k=candidate_k, filters=filters)
        dense_results = self.dense.search(query, top_k=candidate_k, filters=filters)

        merged: dict[str, dict[str, Any]] = {}
        self._accumulate_rrf_scores(merged, bm25_results, "bm25", self.bm25_weight)
        self._accumulate_rrf_scores(merged, dense_results, "dense", self.dense_weight)

        ranked_results = sorted(
            merged.values(),
            key=lambda item: item["hybrid_score"],
            reverse=True,
        )
        reranked_results = rerank_results(
            ranked_results,
            route=route,
            top_k=top_k,
        )
        for result in reranked_results:
            result.setdefault("query_route", route.to_dict())
        return reranked_results

    def _accumulate_rrf_scores(
        self,
        merged: dict[str, dict[str, Any]],
        results: list[dict[str, Any]],
        source_name: str,
        weight: float,
    ) -> None:
        score_key = f"{source_name}_score"
        rank_key = f"{source_name}_rank"
        for rank, result in enumerate(results, start=1):
            chunk_id = result["chunk_id"]
            entry = merged.get(chunk_id)
            if entry is None:
                entry = dict(result)
                entry.setdefault("bm25_score", 0.0)
                entry.setdefault("dense_score", 0.0)
                entry["hybrid_score"] = 0.0
                merged[chunk_id] = entry

            entry[score_key] = result.get(score_key, 0.0)
            entry[rank_key] = rank
            entry["hybrid_score"] += weight * (1.0 / (self.rrf_k + rank))

        LOGGER.debug("Merged %s %s results into hybrid ranking", len(results), source_name)
