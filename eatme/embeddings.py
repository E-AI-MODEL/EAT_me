from __future__ import annotations

from typing import Any, Callable


class EmbeddingEngine:
    """Small optional wrapper for caller-provided embedding functions."""

    def __init__(self, encode_func: Callable[[str], Any] | None = None, similarity_func: Callable[[Any, Any], float] | None = None):
        self.encode_func = encode_func
        self.similarity_func = similarity_func

    def encode(self, text: str) -> Any:
        if self.encode_func is None:
            raise RuntimeError("EmbeddingEngine requires an encode_func or optional embedding backend.")
        return self.encode_func(text)

    def similarity(self, a: Any, b: Any) -> float:
        if self.similarity_func is None:
            raise RuntimeError("EmbeddingEngine requires a similarity_func or optional embedding backend.")
        return float(self.similarity_func(a, b))
