from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.schema import Club, Event

router = APIRouter()

from fastapi.responses import StreamingResponse

class ChatRequest(BaseModel):
    query: str
    history: Optional[List[dict]] = None

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    from rag.generator import generate_answer_stream
    return StreamingResponse(
        generate_answer_stream(request.query, request.history),
        media_type="text/event-stream"
    )


# ── Campus Feed ───────────────────────────────────────────────────────────

@router.get("/feed")
async def get_feed(category: str = "all", limit: int = 30):
    """Return campus feed items. Optionally filter by category."""
    from db.feed_store import feed_store
    items = await feed_store.get_items(category=category, limit=limit)
    return {
        "items": items,
        "meta": feed_store.stats(),
    }


@router.get("/feed/categories")
async def get_feed_categories():
    """Return available feed categories with counts."""
    from db.feed_store import feed_store
    stats = feed_store.stats()
    return {
        "categories": ["All"] + sorted(stats["by_category"].keys()),
        "counts": stats["by_category"],
    }


@router.post("/feed/refresh")
async def refresh_feed():
    """Manually trigger a feed refresh (admin / dev use)."""
    from db.feed_store import feed_store
    await feed_store._refresh()
    return {"status": "ok", "meta": feed_store.stats()}

@router.get("/clubs", response_model=List[Club])
async def get_clubs():
    from db.supabase_client import get_supabase_client
    try:
        supabase = get_supabase_client()
        response = supabase.table("sources").select("*").eq("type", "club").execute()
        clubs = []
        for item in response.data:
            name = item.get("title", "").replace("Club: ", "")
            clubs.append(Club(
                name=name,
                description=item.get("content", ""),
                category="General", # You could infer this or add a category column
                source_url=item.get("source_url", "")
            ))
        return clubs
    except Exception as e:
        print(f"Error fetching clubs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch clubs from database")

@router.get("/events", response_model=List[Event])
async def get_events():
    from db.supabase_client import get_supabase_client
    try:
        supabase = get_supabase_client()
        response = supabase.table("sources").select("*").eq("type", "event").execute()
        events = []
        for item in response.data:
            title = item.get("title", "").replace("Event: ", "")
            events.append(Event(
                title=title,
                date="TBA", # You could extract dates using NLP later
                description=item.get("content", ""),
                source_url=item.get("source_url", "")
            ))
        return events
    except Exception as e:
        print(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch events from database")
