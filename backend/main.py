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
    """Kick off a background feed refresh on startup and run it periodically."""
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

    asyncio.create_task(_init_feed())
    print("[main] vitap-UniOs API started. Background feed refresh loop scheduled (every 30m).")


@app.get("/")
def read_root():
    return {"message": "vitap-UniOs API v2 — Campus Platform for VIT-AP"}
