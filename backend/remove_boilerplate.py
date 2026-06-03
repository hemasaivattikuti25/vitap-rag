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
    # Group chunks by their content
    PRIMARY_AUTHORITIES = {
        "clubs": "https://vitap.ac.in/clubs-and-chapters/",
        "events": "https://vitap.ac.in/events/",
        "news": "https://vitap.ac.in/news/",
        "academics": "https://vitap.ac.in/allschools/",
        "calendar": "https://vitap.ac.in/academiccalender/",
        "research": "https://vitap.ac.in/academic-research/",
        "sporic": "https://vitap.ac.in/sporic/",
        "international": "https://vitap.ac.in/international-relations/",
        "sports": "https://vitap.ac.in/sports/",
        "contact": "https://vitap.ac.in/contact-us/",
        "fees": "https://vitap.ac.in/fees-and-scholarships/",
        "hostel": "https://vitap.ac.in/hostels/",
        "placements": "https://vitap.ac.in/career-development-cell/",
    }

    content_map = {}
    for chunk in chunks:
        text = chunk.get("content", "").strip()
        if text:
            if text not in content_map:
                content_map[text] = []
            content_map[text].append(chunk)

    clean_chunks = []
    for text, occurrences in content_map.items():
        if len(occurrences) <= 2:
            # Low duplication: keep all of them
            clean_chunks.extend(occurrences)
        else:
            # High duplication (boilerplate/nav):
            # Check if any occurrence is on its primary authority page
            kept = False
            for chunk in occurrences:
                category = chunk.get("category", "")
                source_url = chunk.get("source_url", "").rstrip("/")
                authority_url = PRIMARY_AUTHORITIES.get(category, "").rstrip("/")
                
                # If this chunk belongs to the authoritative page for its category, keep ONLY this one!
                if authority_url and authority_url in source_url:
                    clean_chunks.append(chunk)
                    kept = True
                    break
            
            if not kept:
                # If no authority page owns this duplicate content, it is pure boilerplate (e.g. footer) -> Discard all
                pass

    print(f"Clean chunks remaining after authority-aware deduplication: {len(clean_chunks)}")

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
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None, timeout=60.0)
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
