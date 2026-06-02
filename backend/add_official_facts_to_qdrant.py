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
        "Official Fee Structure at VIT-AP University.\n\n"
        "1. B.Tech Tuition Fees (Per Annum):\n"
        "Tuition fees are based on the candidate's VITEEE rank and divided into 5 categories for Group A and Group B specializations.\n"
        "- Group A (Biotechnology, Civil, EEE, Mechanical, etc.):\n"
        "  * Category 1: ₹1,73,000 to ₹1,76,000 per year\n"
        "  * Category 2: ₹2,70,000 per year\n"
        "  * Category 3: ₹3,43,000 per year\n"
        "  * Category 4: ₹4,05,000 per year\n"
        "  * Category 5: ₹4,50,000 per year\n"
        "- Group B (CSE, CSE specializations, ECE, etc.):\n"
        "  * Category 1 (Top Rankers): ₹1,95,000 to ₹1,98,000 per year\n"
        "  * Category 2: ₹3,07,000 per year\n"
        "  * Category 3: ₹4,05,000 per year\n"
        "  * Category 4: ₹4,48,000 per year\n"
        "  * Category 5 (Lower Rankers): ₹4,93,000 per year\n\n"
        "2. Other Popular Programs (Per Annum):\n"
        "- BBA (Bachelor of Business Administration): ₹83,000 per year\n"
        "- B.Sc. / Dual Degree Data Science: ₹58,000 to ₹90,000 per year\n"
        "- M.Sc. Programs: ₹60,000 to ₹80,000 per year\n"
        "- MBA: ₹3,53,000 per year\n"
        "- B.Com / B.A.: ₹50,000 to ₹70,000 per year\n\n"
        "3. Hostel & Mess Fees (Per Annum):\n"
        "- Hostel accommodation and mess charges depend on the room type (AC or Non-AC, single/double/multi-bed occupancy) and chosen mess plan.\n"
        "- The typical range for hostel and mess expenses is ₹1,08,000 to ₹2,22,500 per year.\n\n"
        "Note: A one-time refundable caution deposit of ₹3,000 or ₹5,000 is also charged in the first year."
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
        cloud_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60.0)
        try:
            cloud_client.upsert(collection_name=COLLECTION, points=[point])
            print("Successfully uploaded B.Tech fees to Qdrant Cloud!")
        except Exception as e:
            print(f"Failed to upload to Qdrant Cloud: {e}")

if __name__ == "__main__":
    main()
