import threading

import numpy as np


class Embedder:
    """Embeds supplied keywords locally. Never parses documents or derives keywords."""

    def __init__(self, model_name, cache_dir):
        self.model_name = model_name
        self.cache_dir = str(cache_dir)
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(
                        model_name=self.model_name, cache_dir=self.cache_dir, threads=2
                    )
        return self._model

    def keywords(self, keywords):
        return [v.tolist() for v in self._load().embed(keywords, batch_size=16)]


def cosine(a, b):
    a, b = np.asarray(a), np.asarray(b)
    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denominator) if denominator else 0.0
