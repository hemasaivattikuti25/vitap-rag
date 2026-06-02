from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Club(BaseModel):
    name: str
    description: str
    category: Optional[str] = None
    website: Optional[str] = None
    source_url: str

class Event(BaseModel):
    title: str
    date: str
    club_name: Optional[str] = None
    location: Optional[str] = None
    description: str
    source_url: str

class ExtractedContent(BaseModel):
    title: str
    type: str # 'club', 'event', 'faculty', 'news', 'general'
    content: str
    source_url: str
    updated_at: str
