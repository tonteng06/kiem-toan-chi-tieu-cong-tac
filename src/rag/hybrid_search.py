import numpy as np

from src.models.document import Chunk, SearchResult
from src.rag.bm25_search import BM25Searcher, tokenize
from src.rag.embeddings import EmbeddingModel


def normalise_scores(scores: list[float]) -> list[float]:
    """
    Reused from Week 4 ex2_1_hybrid_search.py.
    Normalise scores to [0, 1] using min-max scaling.
    """
    if not scores:
        return []

    min_s = min(scores)
    max_s = max(scores)

    if max_s == min_s:
        return [1.0] * len(scores)

    return [
        (score - min_s) / (max_s - min_s)
        for score in scores
    ]


class HybridSearcher:
    def __init__(
        self,
        chunks: list[Chunk],
        embedding_model: EmbeddingModel | None = None,
        w_bm25: float = 0.3,
        w_vector: float = 0.7,
    ) -> None:
        self.chunks = chunks
        self.embedding_model = embedding_model or EmbeddingModel()

        self.w_bm25 = w_bm25
        self.w_vector = w_vector

        self.bm25_searcher = BM25Searcher(chunks)

        texts = [
            chunk.content
            for chunk in chunks
        ]

        self.chunk_embeddings = self.embedding_model.encode(texts)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:

        # Step 1: BM25 scores
        query_tokens = tokenize(query)

        raw_bm25_scores = self.bm25_searcher.bm25.get_scores(
            query_tokens
        )

        bm25_norm = np.array(
            normalise_scores(
                [float(score) for score in raw_bm25_scores]
            )
        )

        # Step 2: Dense vector scores
        query_embedding = self.embedding_model.encode_one(query)

        vector_scores = (
            self.chunk_embeddings @ query_embedding
        )

        # Step 3: Week 4 hybrid fusion
        hybrid_scores = (
            self.w_bm25 * bm25_norm
            + self.w_vector * vector_scores
        )

        # Step 4: Rank by hybrid score
        ranked_indices = np.argsort(
            hybrid_scores
        )[::-1][:top_k]

        results: list[SearchResult] = []

        for index in ranked_indices:
            results.append(
                SearchResult(
                    chunk=self.chunks[index],
                    score=float(hybrid_scores[index]),
                    mode="hybrid",
                    dense_score=float(vector_scores[index]),
                    bm25_score=float(raw_bm25_scores[index]),
                )
            )

        return results
