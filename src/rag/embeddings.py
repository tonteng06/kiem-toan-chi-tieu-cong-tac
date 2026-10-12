import numpy as np
from sentence_transformers import SentenceTransformer


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingModel:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> np.ndarray:
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]
