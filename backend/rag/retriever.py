"""
Retriever using local sentence-transformers embeddings.
No API key needed. No quota. Runs 100% locally on the server.
Falls back to Gemini embeddings if sentence-transformers not available.
"""

import os
from typing import List

from qdrant_client import QdrantClient

# ── Local embeddings (primary — free, no API) ─────────────────
try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except ImportError:
    _HAS_ST = False

# ── Qdrant config ──────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")

# Embedding dimension
# sentence-transformers/all-MiniLM-L6-v2 → 384
ST_MODEL_NAME = "all-MiniLM-L6-v2"
ST_DIMENSION  = 384


class QdrantRetriever:
    def __init__(self):
        # ── Connect to Qdrant ──────────────────────────────────
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

        # ── Load embedding model ───────────────────────────────
        self._st_model = None

        if _HAS_ST:
            self._st_model = SentenceTransformer(ST_MODEL_NAME, device="cpu")
            print("[retriever] Embeddings ready (local, no API)")
        else:
            print("[retriever] WARNING: No embedding model available!")

        # Detect which embedding dimension Qdrant index was built with
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
            return ST_DIMENSION

    def _embed(self, text: str) -> List[float]:
        """Generate embedding using best available method."""
        if self._st_model:
            vec = self._st_model.encode(text, normalize_embeddings=True)
            return vec.tolist()

        raise RuntimeError("No embedding model available. Install sentence-transformers.")

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
            print(f"[retriever] Error: {e}")
            return []
