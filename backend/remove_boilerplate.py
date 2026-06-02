import os
import sys
import json
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL     = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION     = "campus_os"
MODEL_NAME     = "all-MiniLM-L6-v2"
DIMENSION      = 384
CACHE_FILE     = "scraped_data_cache.json"

def main():
    if not os.path.exists(CACHE_FILE):
        print(f"Cache file {CACHE_FILE} not found!")
        return

    with open(CACHE_FILE) as f:
        chunks = json.load(f)

    print(f"Total chunks in cache: {len(chunks)}")

    # 1. Detect duplicates (boilerplate text appearing on multiple pages)
    content_counts = {}
    for chunk in chunks:
        text = chunk.get("content", "").strip()
        if text:
            content_counts[text] = content_counts.get(text, 0) + 1

    # Keep only chunks whose content appears in at most 2 different places
    clean_chunks = [c for c in chunks if content_counts.get(c.get("content", "").strip(), 0) <= 2]
    print(f"Clean chunks remaining after removing boilerplate nav/footers: {len(clean_chunks)}")

    # 2. Append student opinions
    opinions_file = "student_opinions.json"
    if os.path.exists(opinions_file):
        with open(opinions_file) as f:
            opinions = json.load(f)
        clean_chunks.extend(opinions)
        print(f"Added {len(opinions)} student opinions. Total: {len(clean_chunks)}")

    # 3. Load model
    print(f"Loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")

    # 4. Connect to Qdrant
    if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
        print(f"Connecting to Qdrant Cloud: {QDRANT_URL}")
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    else:
        path = os.path.join(os.path.dirname(__file__), "local_qdrant")
        print(f"Using local Qdrant at: {path}")
        client = QdrantClient(path=path)

    # 5. Delete + recreate collection
    try:
        client.delete_collection(COLLECTION)
        print("Deleted old collection")
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE),
    )
    print("Created new collection")

    # 6. Embed and upsert
    BATCH = 32
    points = []
    print(f"Embedding {len(clean_chunks)} chunks...")

    for i, chunk in enumerate(clean_chunks):
        text = f"{chunk.get('title', '')} {chunk.get('content', '')}".strip()
        vector = model.encode(text, normalize_embeddings=True).tolist()
        points.append(PointStruct(
            id=i,
            vector=vector,
            payload={
                "title":      chunk.get("title", ""),
                "content":    chunk.get("content", ""),
                "source_url": chunk.get("source_url", ""),
                "category":   chunk.get("category", "general"),
            }
        ))

        if len(points) >= BATCH:
            client.upsert(collection_name=COLLECTION, points=points)
            points = []
            print(f"   Embedded {i+1}/{len(clean_chunks)}...")

    if points:
        client.upsert(collection_name=COLLECTION, points=points)

    # 7. Also upload official B.Tech fees as a high priority point
    # Run the add_official_facts_to_qdrant main logic here to make sure it's present
    from add_official_facts_to_qdrant import main as add_fees_main
    add_fees_main()

    count = client.count(COLLECTION).count
    print(f"Done! {count} vectors indexed in '{COLLECTION}'")

if __name__ == "__main__":
    main()
