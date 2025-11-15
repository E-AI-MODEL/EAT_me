from sentence_transformers import SentenceTransformer, util

class EmbeddingEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def encode(self, text):
        return self.model.encode(text, convert_to_tensor=True)

    def similarity(self, a, b):
        return float(util.pytorch_cos_sim(a, b))
