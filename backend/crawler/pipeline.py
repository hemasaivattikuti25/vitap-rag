import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.vit_site import run_crawler
from db.supabase_client import get_supabase_client
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
import google.generativeai as genai
import uuid

def insert_to_db(data_list):
    try:
        supabase = get_supabase_client()
        
        # Initialize Qdrant locally on disk (no docker/server required)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        local_qdrant_path = os.path.join(base_dir, "local_qdrant")
        client = QdrantClient(path=local_qdrant_path)
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        
        collection_name = "campus_os"
        
        # Create Qdrant collection if it doesn't exist
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
            )
            
        for item in data_list:
            # 1. Insert to Supabase
            supabase.table("sources").insert({
                "title": item.title,
                "type": item.type,
                "content": item.content,
                "source_url": item.source_url,
                "updated_at": item.updated_at
            }).execute()
            
            # 2. Insert to Qdrant
            # Generate embedding
            result = genai.embed_content(
                model="models/gemini-embedding-001",
                content=item.content,
                task_type="retrieval_document",
            )
            embedding = result['embedding']
            
            # Insert point
            client.upsert(
                collection_name=collection_name,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload={
                            "content": item.content,
                            "source_url": item.source_url,
                            "type": item.type
                        }
                    )
                ]
            )
            print(f"Inserted to Supabase and Qdrant: {item.title}")
    except Exception as e:
        print(f"Error inserting into databases: {e}")

if __name__ == "__main__":
    print("Starting crawler pipeline...")
    crawled_data = run_crawler()
    
    if crawled_data:
        print(f"Extracted {len(crawled_data)} records. Pushing to Supabase and Qdrant...")
        insert_to_db(crawled_data)
        print("Pipeline complete.")
    else:
        print("No data extracted.")
