from __future__ import annotations

import logging
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from app.retrieval.indexer import match_filters, prepare_result


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DenseConfig:
    max_features: int = 5000
    n_components: int = 256
    ngram_max: int = 2


class DenseRetriever:
    def __init__(
        self,
        *,
        chunks: list[dict[str, Any]],
        vectorizer: TfidfVectorizer,
        document_vectors: np.ndarray,
        config: DenseConfig,
        svd: TruncatedSVD | None = None,
    ) -> None:
        self.chunks = chunks
        self.vectorizer = vectorizer
        self.document_vectors = document_vectors
        self.config = config
        self.svd = svd

    @classmethod
    def build(cls, chunks: list[dict[str, Any]], config: DenseConfig | None = None) -> "DenseRetriever":
        if not chunks:
            raise ValueError("Cannot build dense index from empty chunks")

        config = config or DenseConfig()
        texts = [chunk.get("text", "") for chunk in chunks]
        vectorizer = TfidfVectorizer(
            max_features=config.max_features,
            ngram_range=(1, config.ngram_max),
            lowercase=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b\w+\b",
        )
        tfidf_matrix = vectorizer.fit_transform(texts)
        feature_count = tfidf_matrix.shape[1]
        doc_count = tfidf_matrix.shape[0]

        if feature_count == 0:
            raise ValueError("Dense index build failed because the TF-IDF vocabulary is empty")

        max_components = min(max(doc_count - 1, 1), max(feature_count - 1, 1), config.n_components)
        svd: TruncatedSVD | None = None

        if max_components >= 2:
            svd = TruncatedSVD(n_components=max_components, random_state=42)
            reduced = svd.fit_transform(tfidf_matrix)
            document_vectors = normalize(reduced)
            LOGGER.info(
                "Built dense index with TF-IDF + SVD (%s docs, %s features, %s dims)",
                doc_count,
                feature_count,
                max_components,
            )
        else:
            document_vectors = normalize(tfidf_matrix).toarray()
            LOGGER.info(
                "Built dense index with normalized TF-IDF fallback (%s docs, %s features)",
                doc_count,
                feature_count,
            )

        return cls(
            chunks=chunks,
            vectorizer=vectorizer,
            document_vectors=np.asarray(document_vectors, dtype=np.float32),
            config=config,
            svd=svd,
        )

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": self.chunks,
            "vectorizer": self.vectorizer,
            "document_vectors": self.document_vectors,
            "config": {
                "max_features": self.config.max_features,
                "n_components": self.config.n_components,
                "ngram_max": self.config.ngram_max,
            },
            "svd": self.svd,
        }
        with output_path.open("wb") as file_handle:
            pickle.dump(payload, file_handle)
        LOGGER.info("Saved dense index to %s", output_path)

    @classmethod
    def load(cls, input_path: Path) -> "DenseRetriever":
        with input_path.open("rb") as file_handle:
            payload = pickle.load(file_handle)
        config = DenseConfig(**payload["config"])
        return cls(
            chunks=payload["chunks"],
            vectorizer=payload["vectorizer"],
            document_vectors=payload["document_vectors"],
            config=config,
            svd=payload["svd"],
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query = query.strip()
        if not query:
            return []

        query_vector = self._encode_query(query)
        if query_vector is None:
            return []

        scores = np.dot(self.document_vectors, query_vector)
        ranked_indices = np.argsort(scores)[::-1]

        results: list[dict[str, Any]] = []
        for doc_index in ranked_indices:
            score = float(scores[doc_index])
            if score <= 0:
                continue
            chunk = self.chunks[int(doc_index)]
            if not match_filters(chunk, filters):
                continue
            results.append(prepare_result(chunk, score, score_key="dense_score"))
            if len(results) >= top_k:
                break
        return results

    def _encode_query(self, query: str) -> np.ndarray | None:
        query_matrix = self.vectorizer.transform([query])
        if query_matrix.shape[1] == 0:
            return None

        if self.svd is not None:
            query_vector = self.svd.transform(query_matrix)
            query_vector = normalize(query_vector)
            return np.asarray(query_vector[0], dtype=np.float32)

        dense_query = normalize(query_matrix).toarray()
        return np.asarray(dense_query[0], dtype=np.float32)
