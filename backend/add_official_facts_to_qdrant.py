import os
import sys
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from fastembed import TextEmbedding
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION = "campus_os"

def main():
    # 1. Text content
    title = "B.Tech Fee Structure - VIT-AP University"
    source_url = "https://vitap.ac.in/fee-structure/"
    content = (
        "Official B.Tech Fee Structure for B.Tech programs at VIT-AP University. "
        "The tuition fees are categorized into four categories:\n"
        "- Category I: ₹1,79,500 per annum\n"
        "- Category II: ₹1,55,500 per annum\n"
        "- Category III: ₹1,31,500 per annum\n"
        "- Category IV: ₹1,07,500 per annum"
    )

    print("Initializing FastEmbed...")
    model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir="./fastembed_cache")
    embeddings = list(model.embed([content]))
    vector = embeddings[0].tolist()

    # Generate a deterministic UUID for this specific content to avoid duplicate point inserts
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, source_url + "#btech_fees"))

    point = PointStruct(
        id=point_id,
        vector=vector,
        payload={
            "title": title,
            "content": content,
            "source_url": source_url,
            "category": "fees"
        }
    )

    # 2. Upload to local
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_path = os.path.join(base_dir, "local_qdrant")
    print(f"Connecting to local Qdrant at {local_path}...")
    local_client = QdrantClient(path=local_path)
    try:
        local_client.upsert(collection_name=COLLECTION, points=[point])
        print("Successfully uploaded B.Tech fees to local Qdrant!")
    except Exception as e:
        print(f"Failed to upload to local Qdrant: {e}")

    # 3. Upload to cloud
    if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
        print(f"Connecting to Qdrant Cloud at {QDRANT_URL}...")
        cloud_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        try:
            cloud_client.upsert(collection_name=COLLECTION, points=[point])
            print("Successfully uploaded B.Tech fees to Qdrant Cloud!")
        except Exception as e:
            print(f"Failed to upload to Qdrant Cloud: {e}")

if __name__ == "__main__":
    main()
