from __future__ import annotations

from typing import Any


class EmbeddingEngine:
    """Small optional wrapper around sentence-transformers similarity.

    The dependency is imported lazily so the core gatekeeper can run without the
    optional embedding stack installed.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)

    def encode(self, text: str) -> Any:
        return self.model.encode(text, convert_to_tensor=True)

    def similarity(self, a: Any, b: Any) -> float:
        from sentence_transformers import util

        return float(util.pytorch_cos_sim(a, b))
