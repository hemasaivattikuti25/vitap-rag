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
            # Use custom local cache dir so it loads instantly from pre-downloaded build files
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            local_cache_path = os.path.join(base_dir, "fastembed_cache")
            self._model = TextEmbedding(model_name=MODEL_NAME, cache_dir=local_cache_path)
            print(f"[retriever] FastEmbed loaded model: {MODEL_NAME} from {local_cache_path}")
        except Exception as e:
            print(f"[retriever] ERROR loading FastEmbed: {e}")
            self._model = None

        self._embedding_dim = self._detect_collection_dim()

        # 3. Load faculty profiles for exact name matching
        self.faculty_profiles = []
        try:
            import json
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_path = os.path.join(base_dir, "scraped_faculty_profiles.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r") as f:
                    self.faculty_profiles = json.load(f)
                print(f"[retriever] Loaded {len(self.faculty_profiles)} faculty profiles for exact name matching.")
        except Exception as e:
            print(f"[retriever] Failed to load faculty profiles cache: {e}")

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
        """Retrieve top-k relevant chunks from Qdrant/Profiles for the query."""
        try:
            matched_profiles = []
            query_lower = query.lower()

            # Normalize query to make split matching robust
            query_clean = ""
            for char in query_lower:
                if char.isalnum() or char.isspace():
                    query_clean += char
                else:
                    query_clean += " "
            query_words = set(query_clean.split())

            # Check if any faculty member's name is referenced in the query
            for p in self.faculty_profiles:
                name = p.get("name", "")
                if not name or name == "Unknown":
                    continue
                
                name_lower = name.lower()
                # Remove common titles
                name_clean = name_lower.replace("dr.", "").replace("prof.", "").replace("mr.", "").replace("ms.", "").strip()
                
                # Normalize clean name
                name_norm = ""
                for char in name_clean:
                    if char.isalnum() or char.isspace():
                        name_norm += char
                    else:
                        name_norm += " "
                
                # Split and filter out tiny name tokens (like initials)
                name_words = [w.strip() for w in name_norm.split() if len(w.strip()) > 2]
                
                # Check if query mentions this faculty name
                is_match = False
                if name_clean and name_clean in query_lower:
                    is_match = True
                else:
                    for w in name_words:
                        if w in query_words:
                            is_match = True
                            break
                
                if is_match:
                    # Strip footer boilerplate to keep chunk text clean and high density
                    content = p.get("content", "")
                    markers = [
                        "“ INDIA should lead",
                        "“INDIA should lead",
                        "INDIA should lead the world",
                        "Quick Links",
                        "Careers",
                        "Hostels",
                        "Transport"
                    ]
                    for marker in markers:
                        if marker in content:
                            content = content.split(marker)[0].strip()
                            
                    text_block = (
                        f"Faculty Profile: {p['name']}\n"
                        f"Designation: {p['designation']}\n"
                        f"School: {p['school']}\n"
                        f"Specialization: {p['specialization']}\n"
                        f"Email: {p['email']}\n"
                        f"Office Address: {p['office_address']}\n"
                        f"Contact No: {p['contact_no']}\n"
                        f"Profile Details: {content}"
                    )
                    
                    matched_profiles.append({
                        "content": text_block,
                        "source_url": p.get("source_url", ""),
                        "title": f"Faculty Profile: {p['name']} ({p['designation']})",
                        "score": 1.0,  # Direct match score
                    })

            # Run vector search
            query_vector = self._embed(query)
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k,
            )
            results_raw = response.points if hasattr(response, "points") else response
            
            vector_results = [
                {
                    "content":    hit.payload.get("content", ""),
                    "source_url": hit.payload.get("source_url", ""),
                    "title":      hit.payload.get("title", ""),
                    "score":      hit.score,
                }
                for hit in results_raw
            ]

            # Merge matched profiles and vector results, preserving exact matches first
            combined = []
            seen_urls = set()
            
            for mp in matched_profiles:
                combined.append(mp)
                seen_urls.add(mp["source_url"])
                
            for vr in vector_results:
                if vr["source_url"] not in seen_urls:
                    combined.append(vr)
                    seen_urls.add(vr["source_url"])
                    
            return combined[:top_k]

        except Exception as e:
            print(f"[retriever] Error during retrieval: {e}")
            return []

