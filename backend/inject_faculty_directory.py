"""
inject_faculty_directory.py
---------------------------
Injects per-school faculty directory chunks into Qdrant.
Each chunk lists all faculty in a school with their cabin number,
email, and extension so queries like "cabin number of SCOPE faculty"
or "who are the faculty in SENSE" work correctly.
"""

import os
import json
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from fastembed import TextEmbedding
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

QDRANT_URL     = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION     = "campus_os"
BACKEND_DIR    = os.path.dirname(os.path.abspath(__file__))


def get_clients():
    clients = []
    local_path = os.path.join(BACKEND_DIR, "local_qdrant")
    clients.append(("local", QdrantClient(path=local_path)))
    if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
        clients.append(("cloud", QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60.0)))
    return clients


def build_faculty_directory_chunks(profiles):
    """Build one chunk per school listing all faculty with cabin + contact info."""
    by_school = defaultdict(list)
    for p in profiles:
        school = p.get("school", "Unknown").strip()
        by_school[school].append(p)

    chunks = []

    # Also build one global "all faculty" chunk
    all_lines = [
        "VIT-AP Faculty Directory — Cabin Numbers, Emails & Extensions\n",
        "=" * 60,
        "Name | School | Cabin | Email | Extension",
        "-" * 60,
    ]

    for school, profs in sorted(by_school.items()):
        school_short = (
            school.replace("SCHOOL OF ", "")
                  .replace("School of ", "")
                  .strip()
        )

        lines = [
            f"Faculty Directory — {school}",
            f"Total: {len(profs)} faculty members\n",
            f"{'Name':<35} {'Cabin':<15} {'Email':<40} {'Ext':<8}",
            "-" * 100,
        ]

        for p in sorted(profs, key=lambda x: x.get("name", "")):
            name     = p.get("name", "Unknown")
            cabin    = p.get("office_address", "N/A")
            email    = p.get("email", "N/A")
            ext      = p.get("contact_no", "N/A")

            lines.append(f"{name:<35} {cabin:<15} {email:<40} {ext}")
            all_lines.append(f"{name} | {school_short} | {cabin} | {email} | {ext}")

        content = "\n".join(lines)
        chunks.append({
            "title":      f"Faculty Directory — {school}",
            "content":    content,
            "source_url": "https://vitap.ac.in/allschools/",
            "category":   "faculty_directory",
            "anchor":     f"faculty_dir_{school[:20].lower().replace(' ', '_')}",
        })

    # Global all-faculty chunk
    chunks.append({
        "title":      "VIT-AP Complete Faculty Directory — All Schools — Cabin Numbers & Contacts",
        "content":    "\n".join(all_lines),
        "source_url": "https://vitap.ac.in/allschools/",
        "category":   "faculty_directory",
        "anchor":     "faculty_dir_all",
    })

    return chunks


def main():
    profiles_path = os.path.join(BACKEND_DIR, "scraped_faculty_profiles.json")
    if not os.path.exists(profiles_path):
        print("[inject_faculty_directory] ERROR: scraped_faculty_profiles.json not found!")
        return

    with open(profiles_path) as f:
        profiles = json.load(f)
    print(f"[inject_faculty_directory] Loaded {len(profiles)} faculty profiles.")

    chunks = build_faculty_directory_chunks(profiles)
    print(f"[inject_faculty_directory] Built {len(chunks)} directory chunks.")

    model = TextEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        cache_dir=os.path.join(BACKEND_DIR, "fastembed_cache")
    )

    points = []
    for chunk in chunks:
        text_to_embed = chunk["title"] + "\n" + chunk["content"]
        vec = list(model.embed([text_to_embed]))[0].tolist()
        points.append(PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk["anchor"])),
            vector=vec,
            payload={
                "title":      chunk["title"],
                "content":    chunk["content"],
                "source_url": chunk["source_url"],
                "category":   chunk["category"],
            }
        ))

    for label, client in get_clients():
        try:
            # Ensure collection exists
            try:
                client.get_collection(COLLECTION)
            except Exception:
                client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                print(f"[inject_faculty_directory] Created collection '{COLLECTION}' in {label}")

            client.upsert(collection_name=COLLECTION, points=points)
            print(f"[inject_faculty_directory] ✅ {len(points)} directory chunks → {label} Qdrant")
        except Exception as e:
            print(f"[inject_faculty_directory] ❌ {label} failed: {e}")

    print("[inject_faculty_directory] Done.\n")


if __name__ == "__main__":
    main()
