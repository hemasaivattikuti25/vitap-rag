import os
import sys
import uuid
import httpx
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from fastembed import TextEmbedding

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION = "campus_os"
URL = "https://vitap.ac.in/affidavit"

def chunk_text(text: str, title: str, source_url: str, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    chunks = []
    words = text.split()
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        content = " ".join(chunk_words)
        if len(content.strip()) > 50:
            chunks.append({
                "title": title,
                "content": content,
                "source_url": source_url
            })
        i += chunk_size - overlap
    return chunks

def main():
    if not QDRANT_URL or not QDRANT_API_KEY:
        print("Error: QDRANT_URL and QDRANT_API_KEY must be set in your environment variables.")
        sys.exit(1)

    print(f"Fetching content from: {URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        resp = httpx.get(URL, headers=headers, follow_redirects=True, timeout=15.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to fetch affidavit page: {e}")
        sys.exit(1)

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # Remove script, style, navigation and footer elements
    for element in soup(["script", "style", "nav", "footer", "header"]):
        element.extract()

    title = soup.title.get_text(strip=True) if soup.title else "VIT-AP Affidavit & Rules"
    body_text = soup.get_text(separator=" ", strip=True)

    print(f"Extracted {len(body_text)} characters. Chunking text...")
    chunks = chunk_text(body_text, title, URL)
    print(f"Created {len(chunks)} chunks.")

    print("Initializing FastEmbed...")
    model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir="./fastembed_cache")

    print(f"Connecting to Qdrant Cloud at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

    print("Generating embeddings and preparing points...")
    points = []
    for idx, chunk in enumerate(chunks):
        content = chunk["content"]
        # Generate embedding
        embeddings = list(model.embed([content]))
        vector = embeddings[0].tolist()
        
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{URL}#chunk{idx}"))
        points.append(
            PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "title": f"Affidavit & Rules: {chunk['title']}",
                    "content": content,
                    "source_url": chunk["source_url"]
                }
            )
        )

    print(f"Uploading {len(points)} vectors to Qdrant Cloud...")
    try:
        client.upsert(
            collection_name=COLLECTION,
            points=points
        )
        print("Successfully uploaded all affidavit rules to Qdrant Cloud!")
    except Exception as e:
        print(f"Failed to upload points to Qdrant: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
