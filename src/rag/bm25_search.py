import re

import numpy as np
from rank_bm25 import BM25Okapi

from src.models.document import Chunk, SearchResult


def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


class BM25Searcher:
    def __init__(
        self,
        chunks: list[Chunk],
    ) -> None:
        self.chunks = chunks

        self.tokenized_chunks = [
            tokenize(chunk.content)
            for chunk in chunks
        ]

        self.bm25 = BM25Okapi(self.tokenized_chunks)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:
        query_tokens = tokenize(query)

        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results: list[SearchResult] = []

        for index in ranked_indices:
            score = float(scores[index])

            results.append(
                SearchResult(
                    chunk=self.chunks[index],
                    score=score,
                    mode="bm25",
                    dense_score=None,
                    bm25_score=score,
                )
            )

        return results
