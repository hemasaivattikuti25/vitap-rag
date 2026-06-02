"""
In-memory feed store with auto-refresh.
No database needed — feed is cached in memory and refreshed every 4 hours.
SQLite-free, zero external dependencies beyond what's already installed.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FeedStore:
    """Thread-safe in-memory feed cache with background refresh."""

    REFRESH_INTERVAL_SECONDS = 4 * 60 * 60  # 4 hours

    def __init__(self):
        self._items: List[Dict] = []
        self._last_refreshed: Optional[datetime] = None
        self._refreshing: bool = False

    def is_stale(self) -> bool:
        if self._last_refreshed is None:
            return True
        age = (datetime.now(timezone.utc) - self._last_refreshed).total_seconds()
        return age > self.REFRESH_INTERVAL_SECONDS

    async def get_items(
        self,
        category: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict]:
        """Return feed items, refreshing if stale."""
        if self.is_stale() and not self._refreshing:
            await self._refresh()

        items = self._items
        if category and category.lower() != "all":
            items = [i for i in items if i.get("category", "").lower() == category.lower()]

        return items[:limit]

    async def _refresh(self):
        """Fetch fresh feed items from crawler."""
        self._refreshing = True
        try:
            from crawler.feed_crawler import fetch_feed_items, CURATED_ITEMS
            print("[feed_store] Refreshing feed...")
            fresh = await fetch_feed_items()

            # Always include curated items at the end as stable fallback
            curated_titles = {i["title"] for i in CURATED_ITEMS}
            existing_titles = {i["title"] for i in fresh}

            merged = list(fresh)
            for item in CURATED_ITEMS:
                if item["title"] not in existing_titles:
                    merged.append(item)

            self._items = merged if merged else CURATED_ITEMS
            self._last_refreshed = datetime.now(timezone.utc)
            print(f"[feed_store] Feed updated: {len(self._items)} items")
        except Exception as e:
            print(f"[feed_store] Refresh failed: {e}. Using curated fallback.")
            if not self._items:
                from crawler.feed_crawler import CURATED_ITEMS
                self._items = CURATED_ITEMS
                self._last_refreshed = datetime.now(timezone.utc)
        finally:
            self._refreshing = False

    def last_updated(self) -> str:
        if self._last_refreshed is None:
            return "Never"
        return self._last_refreshed.isoformat()

    def stats(self) -> Dict:
        cats: Dict[str, int] = {}
        for item in self._items:
            c = item.get("category", "Other")
            cats[c] = cats.get(c, 0) + 1
        return {
            "total": len(self._items),
            "by_category": cats,
            "last_updated": self.last_updated(),
            "is_stale": self.is_stale(),
        }


# Global singleton
feed_store = FeedStore()
