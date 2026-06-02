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

def _infer_club_category(name: str, desc: str) -> str:
    t = (name + " " + desc).lower()
    if any(k in t for k in ["coding", "acm", "ieee", "microsoft", "google", "developer", "hackathon", "robotics", "tech", "computer", "linux", "cloud", "ai", "cyber", "design", "gaming"]):
        return "Technical"
    if any(k in t for k in ["music", "dance", "cultural", "drama", "arts", "movie", "theatre", "fashion", "photography", "film", "radio", "media"]):
        return "Cultural"
    if any(k in t for k in ["sports", "cricket", "football", "basketball", "chess", "gaming", "athletics", "badminton", "fitness", "yoga"]):
        return "Sports"
    if any(k in t for k in ["literary", "debate", "english", "writing", "reading", "poetry", "tedx", "toastmasters"]):
        return "Literary"
    if any(k in t for k in ["social", "rotaract", "ngo", "help", "nature", "green", "youth", "welfare"]):
        return "Social"
    if any(k in t for k in ["physics", "chemistry", "math", "science", "research", "space", "astronomy"]):
        return "Science"
    if any(k in t for k in ["management", "business", "entrepreneur", "startups", "finance", "marketing", "placement", "career"]):
        return "Management"
    return "Other"


@router.get("/clubs", response_model=List[Club])
async def get_clubs():
    from db.supabase_client import get_supabase_client
    from db.feed_store import feed_store
    
    clubs_dict = {}
    
    # 1. Fetch from SQLite DB (sources table)
    try:
        supabase = get_supabase_client()
        response = supabase.table("sources").select("*").eq("type", "club").execute()
        for item in response.data:
            name = item.get("title", "").replace("Club: ", "").strip()
            if name:
                desc = item.get("content", "")
                cat = _infer_club_category(name, desc)
                clubs_dict[name.lower()] = Club(
                    name=name,
                    description=desc,
                    category=cat,
                    source_url=item.get("source_url", "")
                )
    except Exception as e:
        print(f"Error fetching clubs from DB: {e}")

    # 2. Merge items from feed_store with category "Club"
    try:
        feed_items = await feed_store.get_items(category="Club", limit=100)
        for item in feed_items:
            name = item.get("title", "").replace("Club: ", "").strip()
            # Clean up generic names or skip them
            if not name or len(name) < 4 or any(k in name.lower() for k in ["official clubs", "clubs & chapters", "club recruitment"]):
                continue
            name_lower = name.lower()
            if name_lower not in clubs_dict:
                desc = item.get("description") or "Explore activities, events, and workshops organized by this student club at VIT-AP."
                cat = _infer_club_category(name, desc)
                clubs_dict[name_lower] = Club(
                    name=name,
                    description=desc,
                    category=cat,
                    source_url=item.get("source_url", "")
                )
    except Exception as e:
        print(f"Error fetching clubs from feed_store: {e}")

    # Fallback to curated mock if empty
    if not clubs_dict:
        return [
            Club(
                name="Microsoft Student Chapter",
                description="A community of tech enthusiasts exploring Microsoft technologies and building innovative solutions.",
                category="Technical",
                source_url="https://vitap.ac.in/clubs-and-chapters/"
            ),
            Club(
                name="Google Developer Student Club",
                description="Bridge the gap between theory and practice through Google developer tools and technologies.",
                category="Technical",
                source_url="https://vitap.ac.in/clubs-and-chapters/"
            )
        ]

    return list(clubs_dict.values())


@router.get("/events", response_model=List[Event])
async def get_events():
    from db.supabase_client import get_supabase_client
    from db.feed_store import feed_store
    
    events_dict = {}
    
    # 1. Fetch from SQLite DB
    try:
        supabase = get_supabase_client()
        response = supabase.table("sources").select("*").eq("type", "event").execute()
        for item in response.data:
            title = item.get("title", "").replace("Event: ", "").strip()
            if title:
                events_dict[title.lower()] = Event(
                    title=title,
                    date="TBA",
                    club_name=None,
                    location="Campus",
                    description=item.get("content", ""),
                    source_url=item.get("source_url", "")
                )
    except Exception as e:
        print(f"Error fetching events from DB: {e}")

    # 2. Merge items from feed_store with category in ("Event", "Workshop", "Hackathon")
    try:
        for cat in ["Event", "Workshop", "Hackathon"]:
            feed_items = await feed_store.get_items(category=cat, limit=100)
            for item in feed_items:
                title = item.get("title", "").replace("Event: ", "").strip()
                if not title or len(title) < 5 or any(k in title.lower() for k in ["all events", "enriching campus life"]):
                    continue
                title_lower = title.lower()
                if title_lower not in events_dict:
                    # Try to extract date
                    date_str = item.get("date_str") or "Upcoming"
                    events_dict[title_lower] = Event(
                        title=title,
                        date=date_str,
                        club_name=None,
                        location="VIT-AP Campus",
                        description=item.get("description") or f"Join the {title} event/workshop organized at VIT-AP. Scan the source link for details.",
                        source_url=item.get("source_url", "")
                    )
    except Exception as e:
        print(f"Error fetching events from feed_store: {e}")

    if not events_dict:
        return [
            Event(
                title="Tech Hackathon 2026",
                date="June 15, 2026",
                club_name="Microsoft Student Chapter",
                location="Academic Block 1",
                description="A 48-hour hackathon focused on building AI solutions for real-world problems.",
                source_url="https://vitap.ac.in/events/"
            )
        ]

    return list(events_dict.values())
