"""
In-memory LRU cache for chat answers.
Repeated questions are served instantly without any API call.
"""

import time
from collections import OrderedDict
from typing import Tuple, List, Optional


class AnswerCache:
    def __init__(self, max_size: int = 500, ttl_seconds: int = 3600):
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self.max_size = max_size
        self.ttl = ttl_seconds

    def _normalize_key(self, query: str) -> str:
        """Normalize query so near-identical questions hit the same cache entry."""
        return query.lower().strip().rstrip("?!.").replace("  ", " ")

    def get(self, query: str) -> Optional[Tuple[str, List[str]]]:
        key = self._normalize_key(query)
        entry = self._cache.get(key)
        if not entry:
            return None
        if time.time() - entry["ts"] > self.ttl:
            del self._cache[key]
            return None
        # Move to end (LRU)
        self._cache.move_to_end(key)
        return entry["answer"], entry["citations"]

    def set(self, query: str, answer: str, citations: List[str]) -> None:
        key = self._normalize_key(query)
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = {"answer": answer, "citations": citations, "ts": time.time()}
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)  # Evict oldest

    def size(self) -> int:
        return len(self._cache)


# Global singleton
answer_cache = AnswerCache(max_size=500, ttl_seconds=3600)
