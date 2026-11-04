"""Optional local embedding generation using FastEmbed."""

from collections.abc import Sequence


DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"


class LocalEmbedder:
    """Generate normalized text embeddings without sending text to a hosted API."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        try:
            from fastembed import TextEmbedding
        except ImportError as exc:
            raise RuntimeError(
                "Local semantic memory requires the optional dependency. "
                "Install it with: pip install 'flux-agent[memory]'"
            ) from exc
        self.model_name = model_name
        self._model = TextEmbedding(model_name=model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("Embedding input must contain non-empty text.")
        vectors = []
        for vector in self._model.embed(list(texts)):
            values = [float(value) for value in vector]
            if not values:
                raise RuntimeError("The embedding model returned an empty vector.")
            vectors.append(values)
        if len(vectors) != len(texts):
            raise RuntimeError("The embedding model returned an unexpected number of vectors.")
        return vectors

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
