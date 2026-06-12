from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.routes import router

app = FastAPI(title="vitap-UniOs API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    """Kick off periodic background tasks on startup."""
    async def _init_feed():
        # Wait 3s for the server to fully start before crawling
        await asyncio.sleep(3)
        from db.feed_store import feed_store
        
        while True:
            try:
                print("[main] Starting periodic background feed crawl...")
                await feed_store._refresh()
                print("[main] Background feed crawl completed successfully.")
            except Exception as e:
                print(f"[main] Error during background feed crawl: {e}")
            
            # Sleep 30 minutes before next crawl
            await asyncio.sleep(30 * 60)

    async def _init_index_rebuild():
        # Wait 20s for the server to settle before first background rebuild
        await asyncio.sleep(20)
        
        while True:
            try:
                print("[main] Starting periodic background index rebuild...")
                
                # 1. Scraping latest data
                print("[main] [Rebuild] Scraping live website...")
                p1 = await asyncio.create_subprocess_exec(
                    sys.executable, "rebuild_index.py", "--force",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                await p1.communicate()
                
                # 2. Filtering boilerplate and indexing main chunks
                print("[main] [Rebuild] Removing boilerplate & indexing main chunks...")
                p2 = await asyncio.create_subprocess_exec(
                    sys.executable, "remove_boilerplate.py",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                await p2.communicate()
                
                # 3. Reloading and restoring faculty profiles
                print("[main] [Rebuild] Restoring faculty profiles to index...")
                p3 = await asyncio.create_subprocess_exec(
                    sys.executable, "reprocess_faculty_cache.py",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.path.dirname(os.path.abspath(__file__))
                )
                await p3.communicate()
                
                print("[main] Background index rebuild completed successfully.")
            except Exception as e:
                print(f"[main] Error during background index rebuild: {e}")
            
            # Sleep 12 hours before rebuilding again
            await asyncio.sleep(12 * 60 * 60)

    asyncio.create_task(_init_feed())
    asyncio.create_task(_init_index_rebuild())
    print("[main] vitap-UniOs API started. Background feed refresh and index rebuild loops scheduled.")


@app.get("/")
def read_root():
    return {"message": "vitap-UniOs API v2 — Campus Platform for VIT-AP"}
