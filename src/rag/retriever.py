from src.models.document import Chunk, SearchResult
from src.rag.dense_search import DenseSearcher
from src.rag.embeddings import EmbeddingModel
from src.rag.hybrid_search import HybridSearcher


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
    ) -> None:
        self.chunks = chunks

        self.embedding_model = EmbeddingModel()

        self.dense_searcher = DenseSearcher(
            chunks=self.chunks,
            embedding_model=self.embedding_model,
        )

        self.hybrid_searcher = HybridSearcher(
            chunks=self.chunks,
            embedding_model=self.embedding_model,
        )

    def retrieve(
        self,
        query: str,
        mode: str = "hybrid",
        top_k: int = 3,
    ) -> list[SearchResult]:

        if mode == "dense":
            return self.dense_searcher.search(
                query=query,
                top_k=top_k,
            )

        if mode == "hybrid":
            return self.hybrid_searcher.search(
                query=query,
                top_k=top_k,
            )

        raise ValueError(
            f"Unsupported retrieval mode: {mode}. "
            "Use 'dense' or 'hybrid'."
        )
