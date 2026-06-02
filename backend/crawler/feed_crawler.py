"""
Campus Feed Crawler — fetches events, workshops, clubs, hackathons from VIT-AP
Uses async httpx + BeautifulSoup. Fully free, no API keys needed.
Falls back to DuckDuckGo news search when direct scrape yields nothing.
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import List, Dict
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

# VIT-AP pages to crawl for news/events
VIT_AP_SOURCES = [
    {"url": "https://vitap.ac.in/events",             "category": "Event"},
    {"url": "https://vitap.ac.in/news",               "category": "News"},
    {"url": "https://vitap.ac.in/workshops",          "category": "Workshop"},
    {"url": "https://vitap.ac.in/clubs",              "category": "Club"},
    {"url": "https://vitap.ac.in/placements",         "category": "Placement"},
    {"url": "https://vitap.ac.in/admissions",         "category": "Admission"},
    {"url": "https://vitap.ac.in/research",           "category": "Research"},
]

# Fallback DDG searches to fill the feed
DDG_QUERIES = [
    ("site:vitap.ac.in event OR workshop OR hackathon", "Event"),
    ("VIT AP university internship OR hackathon 2025", "Opportunity"),
    ("VIT AP university club recruitment 2025", "Club"),
    ("VIT AP placement 2025 company visit", "Placement"),
]


def _guess_category_from_text(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["hackathon", "code", "coding", "contest", "compete"]): return "Hackathon"
    if any(k in t for k in ["workshop", "seminar", "webinar", "talk", "lecture"]):  return "Workshop"
    if any(k in t for k in ["internship", "intern", "opportunity", "job", "career"]): return "Internship"
    if any(k in t for k in ["club", "chapter", "society", "member", "recruit"]):    return "Club"
    if any(k in t for k in ["placement", "placed", "company", "microsoft", "google", "amazon"]): return "Placement"
    if any(k in t for k in ["research", "paper", "journal", "publication"]):        return "Research"
    if any(k in t for k in ["admission", "apply", "application", "fee", "scholarship"]): return "Admission"
    return "News"


async def _scrape_vitap_page(client: httpx.AsyncClient, url: str, default_cat: str) -> List[Dict]:
    """Scrape a VIT-AP page and extract article/card headings as feed items."""
    items = []
    try:
        resp = await client.get(url, timeout=8.0)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try common patterns: cards, articles, list items
        candidates = (
            soup.find_all("article") or
            soup.find_all("div", class_=re.compile(r"card|event|news|item|post", re.I)) or
            soup.find_all("li", class_=re.compile(r"event|news|item|list", re.I))
        )

        for el in candidates[:15]:
            # Find the best heading
            heading = el.find(["h1", "h2", "h3", "h4", "h5", "a"])
            if not heading:
                continue
            title = heading.get_text(strip=True)
            if len(title) < 10 or len(title) > 200:
                continue

            # Find link
            link_el = el.find("a", href=True)
            href = link_el["href"] if link_el else url
            if href.startswith("/"):
                href = "https://vitap.ac.in" + href

            # Find description snippet
            desc_el = el.find("p")
            desc = desc_el.get_text(strip=True)[:200] if desc_el else ""

            # Find date
            date_el = el.find(["time", "span", "p"], string=re.compile(r"\d{4}|\d{1,2}\s+\w+"))
            date_str = date_el.get_text(strip=True) if date_el else ""

            category = _guess_category_from_text(title + " " + desc) if default_cat == "News" else default_cat

            items.append({
                "title": title,
                "description": desc,
                "category": category,
                "source_url": href,
                "date_str": date_str,
                "source": "vitap.ac.in",
            })

    except Exception as e:
        print(f"[feed_crawler] Failed to scrape {url}: {e}")

    return items


async def _ddg_news_search(client: httpx.AsyncClient, query: str, category: str) -> List[Dict]:
    """Search DuckDuckGo HTML for VIT-AP news/events."""
    items = []
    try:
        url = "https://html.duckduckgo.com/html/"
        resp = await client.get(url, params={"q": query}, timeout=8.0)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        for div in soup.find_all("div", class_="result__body")[:6]:
            title_el = div.find("a", class_="result__a") or div.find("a", class_="result__url")
            snippet_el = div.find("a", class_="result__snippet")

            if not title_el:
                continue

            title = title_el.get_text(strip=True)
            if len(title) < 10:
                continue

            href = title_el.get("href", "")
            import urllib.parse
            if "uddg=" in href:
                parsed = urllib.parse.urlparse(href)
                qs = urllib.parse.parse_qs(parsed.query)
                href = qs.get("uddg", [href])[0]

            snippet = snippet_el.get_text(strip=True)[:200] if snippet_el else ""
            cat = _guess_category_from_text(title + " " + snippet)

            items.append({
                "title": title,
                "description": snippet,
                "category": cat,
                "source_url": href,
                "date_str": "",
                "source": "web",
            })

    except Exception as e:
        print(f"[feed_crawler] DDG search failed for '{query}': {e}")

    return items


async def fetch_feed_items() -> List[Dict]:
    """
    Main entry point. Scrapes VIT-AP pages + DDG fallback.
    Returns a deduplicated list of feed items.
    """
    all_items: List[Dict] = []
    seen_titles = set()

    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as client:
        # 1. Scrape VIT-AP pages in parallel
        tasks = [_scrape_vitap_page(client, s["url"], s["category"]) for s in VIT_AP_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_items.extend(result)

        # 2. DDG searches in parallel
        ddg_tasks = [_ddg_news_search(client, q, cat) for q, cat in DDG_QUERIES]
        ddg_results = await asyncio.gather(*ddg_tasks, return_exceptions=True)
        for result in ddg_results:
            if isinstance(result, list):
                all_items.extend(result)

    # Deduplicate by normalised title
    deduped = []
    for item in all_items:
        key = re.sub(r"\W+", "", item["title"].lower())[:60]
        if key not in seen_titles:
            seen_titles.add(key)
            item["fetched_at"] = datetime.now(timezone.utc).isoformat()
            deduped.append(item)

    print(f"[feed_crawler] Fetched {len(deduped)} unique items")
    return deduped


# ── Fallback curated items (always shown when crawl fails) ────────────────
CURATED_ITEMS = [
    {
        "title": "VIT-AP University — Official Clubs Portal",
        "description": "Explore 70+ clubs across technical, cultural, and sports domains. Find your community at VIT-AP.",
        "category": "Club",
        "source_url": "https://vitap.ac.in/clubs",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "VIT-AP Placements 2024-25 — Latest Updates",
        "description": "Top companies visiting VIT-AP this season. Check placement news and package updates.",
        "category": "Placement",
        "source_url": "https://vitap.ac.in/placements",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "Research Opportunities at VIT-AP",
        "description": "Faculty-led research projects, internships, and publication opportunities for students.",
        "category": "Research",
        "source_url": "https://vitap.ac.in/research",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "VIT-AP International Relations — Exchange Programs",
        "description": "Semester Abroad Program (SAP) and International Transfer Program (ITP) applications open.",
        "category": "Opportunity",
        "source_url": "https://vitap.ac.in/international-relations",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "VIT-AP Academic Calendar 2025",
        "description": "Key dates: exam schedules, holiday list, registration deadlines, and semester timeline.",
        "category": "News",
        "source_url": "https://vitap.ac.in/academic-calendar",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "SCOPE — School of Computer Science & Engineering",
        "description": "Courses, faculty profiles, labs, and events for CSE, AI, and related branches.",
        "category": "News",
        "source_url": "https://vitap.ac.in/scope",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "VIT-AP Scholarships — Apply Now",
        "description": "Merit and need-based scholarships available for eligible students. Check eligibility and apply.",
        "category": "Admission",
        "source_url": "https://vitap.ac.in/scholarships",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
    {
        "title": "Hackathons & Coding Competitions 2025",
        "description": "Upcoming hackathons, competitive programming contests, and coding challenges at VIT-AP.",
        "category": "Hackathon",
        "source_url": "https://vitap.ac.in/events",
        "date_str": "",
        "source": "curated",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    },
]
