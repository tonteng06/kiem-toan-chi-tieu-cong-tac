import numpy as np

from src.models.document import Chunk, SearchResult
from src.rag.embeddings import EmbeddingModel


class DenseSearcher:
    def __init__(
        self,
        chunks: list[Chunk],
        embedding_model: EmbeddingModel | None = None,
    ) -> None:
        self.chunks = chunks
        self.embedding_model = embedding_model or EmbeddingModel()

        texts = [chunk.content for chunk in chunks]

        self.chunk_embeddings = self.embedding_model.encode(texts)

    def search(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[SearchResult]:
        query_embedding = self.embedding_model.encode_one(query)

        scores = self.chunk_embeddings @ query_embedding

        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results: list[SearchResult] = []

        for index in ranked_indices:
            score = float(scores[index])

            results.append(
                SearchResult(
                    chunk=self.chunks[index],
                    score=score,
                    mode="dense",
                    dense_score=score,
                    bm25_score=None,
                )
            )

        return results
