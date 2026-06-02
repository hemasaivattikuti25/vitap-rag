from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from api.routes import router

app = FastAPI(title="CampusOS API", version="2.0.0")

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
    """Kick off a background feed refresh on startup (non-blocking)."""
    async def _init_feed():
        # Wait 3s for the server to fully start before crawling
        await asyncio.sleep(3)
        from db.feed_store import feed_store
        await feed_store._refresh()

    asyncio.create_task(_init_feed())
    print("[main] CampusOS API started. Feed refresh scheduled.")


@app.get("/")
def read_root():
    return {"message": "CampusOS API v2 — Campus Platform for VIT-AP"}
