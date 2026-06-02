#!/usr/bin/env python3
"""
Rebuild Qdrant index using Playwright (handles JS-rendered pages) + sentence-transformers.
Scrapes VIT-AP website deeply and builds a 384-dim local embeddings index.

Usage:
    python rebuild_index.py [--force]   # --force re-scrapes even if cache exists
"""

import os, sys, json, time, asyncio, argparse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# ── Config ────────────────────────────────────────────────────
QDRANT_URL     = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION     = "campus_os"
MODEL_NAME     = "all-MiniLM-L6-v2"
DIMENSION      = 384
CACHE_FILE     = "scraped_data_cache.json"

# VIT-AP pages to scrape (verified working URLs)
PAGES = [
    ("https://vitap.ac.in/",                          "general"),
    ("https://vitap.ac.in/clubs-and-chapters/",       "clubs"),
    ("https://vitap.ac.in/events/",                   "events"),
    ("https://vitap.ac.in/news/",                     "news"),
    ("https://vitap.ac.in/allschools/",               "academics"),
    ("https://vitap.ac.in/academiccalender/",          "academics"),
    ("https://vitap.ac.in/academic-research/",        "research"),
    ("https://vitap.ac.in/sporic/",                   "research"),
    ("https://vitap.ac.in/international-relations/",  "international"),
    ("https://vitap.ac.in/sports/",                   "sports"),
    ("https://vitap.ac.in/contact-us/",               "contact"),
    ("https://vitap.ac.in/fees-and-scholarships/",    "fees"),
    ("https://vitap.ac.in/hostels/",                  "hostel"),
    ("https://vitap.ac.in/career-development-cell/",  "placements"),
]


async def scrape_with_playwright(pages: list) -> list[dict]:
    """Use Playwright to render and scrape JS-heavy pages."""
    from playwright.async_api import async_playwright
    import glob

    # Find the downloaded Chrome executable (headless shell may not be present)
    chrome_paths = glob.glob(
        "/Users/sai2005/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/"
        "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    )
    executable_path = chrome_paths[0] if chrome_paths else None

    chunks = []
    async with async_playwright() as pw:
        launch_kwargs = {"headless": True}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
            print(f"  Using Chrome: {executable_path.split('/')[-1]}")

        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for url, category in pages:
            try:
                print(f"  Scraping [{category}] {url}")
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)  # wait for JS

                # Remove clutter (menus, sidebars, headers, footers, popups, and navigation blocks)
                await page.evaluate("""
                    ['nav', 'footer', 'header', 'script', 'style', '.cookie-banner',
                     '.popup', '#popup', '.modal', 'iframe', '.sidebar', '#sidebar',
                     '.widget', '.menu', '.sub-menu', '.footer-widgets', '#header',
                     '#footer', '.nav-menu', '.mobile-menu', '.top-bar', '.bottom-bar',
                     '.menu-container', '.main-menu', '.navigation', '#navigation',
                     '#menu', '.megamenu', '#megamenu', '.menu-wrapper', '.menu-bar',
                     '.topbar', '#topbar', '.header-wrapper', '#header-wrapper',
                     '.footer-wrapper', '#footer-wrapper', '.sidebar-wrapper', '#sidebar-wrapper',
                     '.widget-area', '#secondary', '.breadcrumbs', '.breadcrumb'].forEach(sel => {
                        document.querySelectorAll(sel).forEach(el => el.remove());
                    });
                """)

                # Extract heading + following text as chunks, tables, and lists
                page_chunks = await page.evaluate("""
                    () => {
                        const chunks = [];
                        const url = window.location.href;
                        const pageTitle = document.title || url;

                        // Helper to add a chunk
                        function addChunk(title, content) {
                            content = content.replace(/\\s+/g, ' ').trim();
                            if (content.length > 50) {
                                chunks.push({
                                    title: title.slice(0, 150),
                                    content: content.slice(0, 1500),
                                    source_url: url
                                });
                            }
                        }

                        // Try to find the main content container
                        const mainContent = document.querySelector('main, article, #content, .content, .entry-content, #main, .main-content, #content-area');
                        const root = mainContent || document.body;

                        // 1. Extract by headings (h1, h2, h3, h4, h5)
                        const headings = root.querySelectorAll('h1, h2, h3, h4, h5');
                        headings.forEach(h => {
                            const title = h.textContent.trim();
                            if (!title || title.length < 2) return;
                            
                            // Collect subsequent elements until next heading
                            let content = '';
                            let el = h.nextElementSibling;
                            let count = 0;
                            while (el && !['H1','H2','H3','H4','H5'].includes(el.tagName) && count < 20) {
                                content += ' ' + (el.textContent || '').trim();
                                el = el.nextElementSibling;
                                count++;
                            }
                            addChunk(title, content);
                        });

                        // 2. Extract tables (crucial for faculty directories and fee lists)
                        const tables = root.querySelectorAll('table');
                        tables.forEach((table, idx) => {
                            let tableText = '';
                            const rows = table.querySelectorAll('tr');
                            rows.forEach(row => {
                                const cells = row.querySelectorAll('th, td');
                                const cellTexts = Array.from(cells).map(c => c.textContent.trim()).filter(Boolean);
                                if (cellTexts.length > 0) {
                                    tableText += cellTexts.join(' | ') + '\\n';
                                }
                            });
                            if (tableText.length > 50) {
                                addChunk(`${pageTitle} - Table ${idx + 1}`, tableText);
                            }
                        });

                        // 3. Extract lists (for clubs list and syllabus lists)
                        const lists = root.querySelectorAll('ul, ol');
                        lists.forEach((list, idx) => {
                            const items = list.querySelectorAll('li');
                            const itemTexts = Array.from(items).map(li => li.textContent.trim()).filter(Boolean);
                            if (itemTexts.length > 2) {
                                addChunk(`${pageTitle} - List ${idx + 1}`, itemTexts.join(', '));
                            }
                        });

                        // 4. Extract paragraphs directly to capture plain text blocks
                        const paragraphs = root.querySelectorAll('p');
                        paragraphs.forEach((p, idx) => {
                            const text = p.textContent.trim();
                            if (text.length > 80) {
                                addChunk(`${pageTitle} - Paragraph ${idx + 1}`, text);
                            }
                        });

                        // 5. Fallback if no chunks found: split whole body text
                        if (chunks.length === 0) {
                            const paras = [];
                            root.querySelectorAll('p, li, td, span').forEach(el => {
                                const t = el.textContent.trim();
                                if (t.length > 30) paras.push(t);
                            });
                            
                            // Group into blocks
                            for (let i = 0; i < paras.length; i += 4) {
                                const block = paras.slice(i, i + 4).join(' ');
                                if (block.length > 50) {
                                    addChunk(pageTitle, block);
                                }
                            }
                        }

                        return chunks;
                    }
                """)

                if page_chunks:
                    chunks.extend(page_chunks)
                    print(f"    ✓ {len(page_chunks)} chunks")
                else:
                    # Last resort: get all visible text
                    text = await page.inner_text("body")
                    text = " ".join(text.split())[:2000]
                    if len(text) > 100:
                        chunks.append({"title": url, "content": text, "source_url": url})
                        print(f"    ✓ 1 chunk (full text fallback)")
                    else:
                        print(f"    ✗ No content")

            except Exception as e:
                print(f"    ✗ Error: {str(e)[:80]}")

            await asyncio.sleep(1)

        await browser.close()

    return chunks


def connect_qdrant() -> QdrantClient:
    if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
        print(f"\n☁️  Connecting to Qdrant Cloud: {QDRANT_URL}")
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    else:
        path = os.path.join(os.path.dirname(__file__), "local_qdrant")
        print(f"\n💾 Using local Qdrant at: {path}")
        return QdrantClient(path=path)


def rebuild_index(client: QdrantClient, chunks: list[dict], model: SentenceTransformer):
    print(f"\n🔄 Rebuilding '{COLLECTION}' (dim={DIMENSION})...")

    # Delete + recreate collection
    try:
        client.delete_collection(COLLECTION)
        print("   Deleted old collection")
    except Exception:
        pass

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=DIMENSION, distance=Distance.COSINE),
    )
    print("   Created new collection")

    # Embed + insert
    BATCH = 32
    points = []
    print(f"\n⚡ Embedding {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
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
            print(f"   Embedded {i+1}/{len(chunks)}...")

    if points:
        client.upsert(collection_name=COLLECTION, points=points)

    count = client.count(COLLECTION).count
    print(f"\n✅ Done! {count} vectors indexed in '{COLLECTION}'")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-scrape even if cache exists")
    args = parser.parse_args()

    print("=" * 55)
    print(" vitap-UniOs — Qdrant Index Rebuild (Playwright)")
    print(" Embeddings: sentence-transformers/all-MiniLM-L6-v2")
    print("=" * 55)

    # Load model
    print(f"\n📦 Loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")
    print("   Model ready!")

    # Scrape / load cache
    if os.path.exists(CACHE_FILE) and not args.force:
        print(f"\n📂 Loading cached data from {CACHE_FILE}")
        with open(CACHE_FILE) as f:
            chunks = json.load(f)
        print(f"   {len(chunks)} chunks loaded")
    else:
        print("\n🌐 Scraping VIT-AP with Playwright...")
        chunks = await scrape_with_playwright(PAGES)
        if not chunks:
            print("❌ No data scraped. Exiting.")
            sys.exit(1)
        with open(CACHE_FILE, "w") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Cached {len(chunks)} chunks to {CACHE_FILE}")

    # Load student opinions
    opinions_file = "student_opinions.json"
    if os.path.exists(opinions_file):
        print(f"\n💬 Loading student opinions from {opinions_file}")
        with open(opinions_file) as f:
            opinions = json.load(f)
        chunks.extend(opinions)
        print(f"   Added {len(opinions)} student opinion chunks")

    # Connect + rebuild
    client = connect_qdrant()
    rebuild_index(client, chunks, model)

    print("\n🎉 Index ready! Restart the backend:")
    print("   ./venv/bin/uvicorn main:app --reload --port 8000\n")


if __name__ == "__main__":
    asyncio.run(main())
