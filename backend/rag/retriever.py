"""
Retriever using FastEmbed (ONNX Runtime) for lightweight embeddings.
No PyTorch/torch dependency, fits easily within Render's 512MB RAM limit.
"""

import os
from typing import List
from qdrant_client import QdrantClient

# Qdrant config
QDRANT_URL     = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# Model config
# fastembed has native support for sentence-transformers/all-MiniLM-L6-v2 (dim=384)
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIMENSION = 384


class QdrantRetriever:
    def __init__(self):
        # 1. Connect to Qdrant
        if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
            # Cloud Qdrant
            self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
            print(f"[retriever] Connected to Qdrant Cloud: {QDRANT_URL}")
        else:
            # Local disk Qdrant
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_path = os.path.join(base_dir, "local_qdrant")
            self.client = QdrantClient(path=local_path)
            print(f"[retriever] Using local Qdrant at: {local_path}")

        self.collection_name = "campus_os"

        # 2. Load embedding model using FastEmbed
        try:
            from fastembed import TextEmbedding
            # This loads the ONNX model and runs on ONNX Runtime (CPU)
            self._model = TextEmbedding(model_name=MODEL_NAME)
            print(f"[retriever] FastEmbed loaded model: {MODEL_NAME}")
        except Exception as e:
            print(f"[retriever] ERROR loading FastEmbed: {e}")
            self._model = None

        self._embedding_dim = self._detect_collection_dim()

    def _detect_collection_dim(self) -> int:
        """Check what dimension the existing Qdrant collection uses."""
        try:
            info = self.client.get_collection(self.collection_name)
            dim = info.config.params.vectors.size
            print(f"[retriever] Collection '{self.collection_name}' uses dim={dim}")
            return dim
        except Exception:
            # Collection may not exist yet
            return DEFAULT_DIMENSION

    def _embed(self, text: str) -> List[float]:
        """Generate embedding using FastEmbed."""
        if not self._model:
            raise RuntimeError("FastEmbed model is not initialized.")
        # self._model.embed returns a generator of numpy arrays.
        # We pass a list [text] and extract the first element.
        embeddings = list(self._model.embed([text]))
        return embeddings[0].tolist()

    def retrieve(self, query: str, top_k: int = 4) -> List[dict]:
        """Retrieve top-k relevant chunks from Qdrant for the query."""
        try:
            query_vector = self._embed(query)

            # Handle both remote QdrantClient and local QdrantLocal
            search_func = getattr(self.client, "search", None)
            if not search_func and hasattr(self.client, "_client"):
                search_func = getattr(self.client._client, "search", None)

            if not search_func:
                raise AttributeError("QdrantClient has no search method.")

            results_raw = search_func(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
            )

            return [
                {
                    "content":    hit.payload.get("content", ""),
                    "source_url": hit.payload.get("source_url", ""),
                    "title":      hit.payload.get("title", ""),
                    "score":      hit.score,
                }
                for hit in results_raw
            ]

        except Exception as e:
            print(f"[retriever] Error during retrieval: {e}")
            return []
