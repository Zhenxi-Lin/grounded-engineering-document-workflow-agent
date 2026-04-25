from __future__ import annotations

import logging
import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.retrieval.indexer import match_filters, prepare_result, tokenize_text


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BM25Config:
    k1: float = 1.5
    b: float = 0.75


class BM25Retriever:
    def __init__(
        self,
        *,
        chunks: list[dict[str, Any]],
        doc_term_freqs: list[dict[str, int]],
        doc_lengths: list[int],
        avg_doc_length: float,
        idf: dict[str, float],
        config: BM25Config,
    ) -> None:
        self.chunks = chunks
        self.doc_term_freqs = doc_term_freqs
        self.doc_lengths = doc_lengths
        self.avg_doc_length = avg_doc_length
        self.idf = idf
        self.config = config

    @classmethod
    def build(cls, chunks: list[dict[str, Any]], config: BM25Config | None = None) -> "BM25Retriever":
        if not chunks:
            raise ValueError("Cannot build BM25 index from empty chunks")

        config = config or BM25Config()
        doc_term_freqs: list[dict[str, int]] = []
        doc_lengths: list[int] = []
        doc_freqs: dict[str, int] = {}

        for chunk in chunks:
            tokens = tokenize_text(chunk.get("text", ""))
            term_freq: dict[str, int] = {}
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
            doc_term_freqs.append(term_freq)
            doc_lengths.append(len(tokens))
            for token in term_freq:
                doc_freqs[token] = doc_freqs.get(token, 0) + 1

        doc_count = len(chunks)
        avg_doc_length = sum(doc_lengths) / doc_count if doc_count else 0.0
        idf = {
            token: math.log(1.0 + ((doc_count - df + 0.5) / (df + 0.5)))
            for token, df in doc_freqs.items()
        }

        LOGGER.info("Built BM25 index for %s chunks with %s unique terms", doc_count, len(idf))
        return cls(
            chunks=chunks,
            doc_term_freqs=doc_term_freqs,
            doc_lengths=doc_lengths,
            avg_doc_length=avg_doc_length,
            idf=idf,
            config=config,
        )

    def save(self, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "chunks": self.chunks,
            "doc_term_freqs": self.doc_term_freqs,
            "doc_lengths": self.doc_lengths,
            "avg_doc_length": self.avg_doc_length,
            "idf": self.idf,
            "config": {
                "k1": self.config.k1,
                "b": self.config.b,
            },
        }
        with output_path.open("wb") as file_handle:
            pickle.dump(payload, file_handle)
        LOGGER.info("Saved BM25 index to %s", output_path)

    @classmethod
    def load(cls, input_path: Path) -> "BM25Retriever":
        with input_path.open("rb") as file_handle:
            payload = pickle.load(file_handle)
        config = BM25Config(**payload["config"])
        return cls(
            chunks=payload["chunks"],
            doc_term_freqs=payload["doc_term_freqs"],
            doc_lengths=payload["doc_lengths"],
            avg_doc_length=payload["avg_doc_length"],
            idf=payload["idf"],
            config=config,
        )

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query_tokens = tokenize_text(query)
        if not query_tokens:
            return []

        scored_results: list[tuple[float, int]] = []
        for doc_index, chunk in enumerate(self.chunks):
            if not match_filters(chunk, filters):
                continue
            score = self._score_document(doc_index, query_tokens)
            if score > 0:
                scored_results.append((score, doc_index))

        scored_results.sort(key=lambda item: item[0], reverse=True)
        top_results = scored_results[:top_k]
        return [
            prepare_result(self.chunks[doc_index], score, score_key="bm25_score")
            for score, doc_index in top_results
        ]

    def _score_document(self, doc_index: int, query_tokens: list[str]) -> float:
        term_freqs = self.doc_term_freqs[doc_index]
        doc_length = self.doc_lengths[doc_index]
        score = 0.0

        for token in query_tokens:
            freq = term_freqs.get(token, 0)
            if freq == 0:
                continue

            idf = self.idf.get(token)
            if idf is None:
                continue

            denominator = freq + self.config.k1 * (
                1.0 - self.config.b + self.config.b * (doc_length / max(self.avg_doc_length, 1e-9))
            )
            score += idf * ((freq * (self.config.k1 + 1.0)) / denominator)

        return score
