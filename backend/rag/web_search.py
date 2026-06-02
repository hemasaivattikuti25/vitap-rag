"""
Web Search Fallback Service using DuckDuckGo HTML search (fully async).
Uses httpx.AsyncClient so it never blocks FastAPI's event loop.
"""

import httpx
import urllib.parse
import re
from bs4 import BeautifulSoup
from typing import List, Dict


def clean_search_query(query: str) -> str:
    """Strip conversational prefixes and question marks to produce keyword searches."""
    lower = query.lower().strip()

    prefixes = [
        "can you tell me who is", "can you tell me what is", "can you tell me about",
        "do you know who is", "do you know what is", "do you know about",
        "who is the", "who is a", "who is",
        "what is the", "what is a", "what is",
        "where is the", "where is a", "where is",
        "tell me about the", "tell me about a", "tell me about",
        "how to reach", "how to get to", "how to",
        "please tell me", "what are the", "what are",
    ]

    cleaned = lower
    for pref in prefixes:
        if cleaned.startswith(pref):
            cleaned = cleaned[len(pref):].strip()
            break

    if cleaned.endswith("?"):
        cleaned = cleaned[:-1].strip()

    return cleaned.strip() or query


def check_is_general(query: str) -> bool:
    """Classify if the query is a general greeting, math, or coding task unrelated to VIT-AP."""
    lower_query = query.strip().lower()

    # 1. Greetings / Casual chat
    greetings = {
        "hi", "hello", "hey", "yo", "hola", "good morning", "good afternoon",
        "how are you", "who are you", "what is your name", "help", "thanks", "thank you",
    }
    if lower_query in greetings:
        return True

    # 2. General math topics or conversion requests
    general_math_keywords = {
        "convert", "decimal", "binary", "hexadecimal", "octal", "plus", "minus",
        "divided by", "multiplied by", "calculate", "derivative", "integral",
        "matrix", "matrices", "equation", "solve for", "trigonometry", "prime number",
        "fibonacci", "factorial", "gcd", "lcm", "square root",
    }
    if any(kw in lower_query for kw in general_math_keywords):
        return True

    # 3. General coding / scripting tasks
    general_coding_keywords = {
        "write a python", "write a code", "implement in java", "sorting algorithm in c",
        "program to", "how to write a", "code in",
    }
    if any(kw in lower_query for kw in general_coding_keywords):
        return True

    # 4. Numeric math expressions (e.g., 2+2, 100 * 5)
    if re.match(r"^[\d\s+\-*/%()=^.x]+$", lower_query) and any(
        op in lower_query for op in ["+", "-", "*", "/", "%", "="]
    ):
        return True

    return False


def _parse_ddg_html(html_text: str, max_results: int) -> List[Dict[str, str]]:
    """Parse DuckDuckGo HTML results page into a list of dicts."""
    results = []
    soup = BeautifulSoup(html_text, "html.parser")
    for div in soup.find_all("div", class_="result__body")[:max_results]:
        title_el = div.find("a", class_="result__url")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        href = title_el.get("href", "")
        if "uddg=" in href:
            parsed = urllib.parse.urlparse(href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                href = qs["uddg"][0]
        snippet_el = div.find("a", class_="result__snippet")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""
        
        # Exclude Reddit, Quora, and generic forums to ensure official accuracy
        lower_href = href.lower()
        if "reddit.com" in lower_href or "quora.com" in lower_href:
            continue
            
        if title or snippet:
            results.append({"title": title, "content": snippet, "source_url": href})
    return results


async def web_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Async search DuckDuckGo HTML and return a list of result dicts.
    Fully non-blocking — uses httpx.AsyncClient so FastAPI event loop is never stalled.
    """
    keyword_query = clean_search_query(query)
    search_query = keyword_query

    # Append "VIT AP" context for campus-specific queries
    if not check_is_general(query) and "vit" not in keyword_query.lower():
        search_query = f"{keyword_query} VIT AP"

    print(f"[web_search] Searching: '{search_query}' (original: '{query}')")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    ddg_url = "https://html.duckduckgo.com/html/"

    # Use a much lower timeout (2.5s) to avoid stalling the chatbot on failures
    async with httpx.AsyncClient(timeout=2.5) as client:
        primary_success = False
        try:
            resp = await client.get(ddg_url, params={"q": search_query}, headers=headers)
            if resp.status_code == 200:
                primary_success = True
                results = _parse_ddg_html(resp.text, max_results)
                if results:
                    print(f"[web_search] Found {len(results)} results")
                    return results
                else:
                    # Check if we were rate limited / CAPTCHAd
                    lowered_text = resp.text.lower()
                    if any(kw in lowered_text for kw in ["captcha", "robot", "forbidden", "check your browser"]):
                        print("[web_search] Blocked by DuckDuckGo CAPTCHA/Rate Limit, bypassing fallback search to save time.")
                        primary_success = False
        except Exception as e:
            print(f"[web_search] Primary search error/timeout: {e}")

        # Fallback search: ONLY try if the primary query succeeded cleanly but yielded 0 results.
        # If the first request timed out or was blocked, the second request will also time out/fail.
        if primary_success and search_query != query:
            try:
                resp = await client.get(ddg_url, params={"q": query}, headers=headers)
                if resp.status_code == 200:
                    results = _parse_ddg_html(resp.text, max_results)
                    print(f"[web_search] Fallback found {len(results)} results")
                    return results
            except Exception as e2:
                print(f"[web_search] Fallback search error: {e2}")

    print("[web_search] Found 0 results")
    return []
