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
            remaining = cleaned[len(pref):]
            # Ensure it is a complete word prefix match (followed by space, punctuation, or end of string)
            if len(remaining) == 0 or remaining[0].isspace() or remaining[0] in ".,!?;:":
                cleaned = remaining.strip()
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
            
        # Ensure we stay strictly in the context of VIT-AP and exclude other VIT campuses (Vellore, Chennai, Bhopal)
        if "vit.ac.in" in lower_href and "vitap.ac.in" not in lower_href:
            continue
        if "vitbhopal.ac.in" in lower_href:
            continue
        if any(campus in lower_href for campus in ["vellore", "chennai", "bhopal"]) and not any(ap in lower_href for ap in ["vitap", "vit-ap"]):
            continue
            
        if title or snippet:
            results.append({"title": title, "content": snippet, "source_url": href})
    return results


def decode_yahoo_url(url: str) -> str:
    """Extract and decode target URL from Yahoo search redirect link."""
    if "RU=" in url:
        import re
        match = re.search(r"RU=([^/]+)", url)
        if match:
            encoded_url = match.group(1)
            import urllib.parse
            return urllib.parse.unquote(encoded_url)
    return url


async def yahoo_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Search Yahoo Search and return list of parsed results."""
    keyword_query = clean_search_query(query)
    search_query = keyword_query
    
    if not check_is_general(query) and "vit" not in keyword_query.lower():
        search_query = f"{keyword_query} VIT AP"
        
    print(f"[yahoo_search] Searching: '{search_query}' (original: '{query}')")
    
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    yahoo_url = "https://search.yahoo.com/search"
    
    results = []
    try:
        async with httpx.AsyncClient(timeout=1.5) as client:
            resp = await client.get(yahoo_url, params={"p": search_query}, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                comp_texts = soup.find_all("div", class_="compText")
                for div in comp_texts[:max_results + 3]:
                    parent = div.parent
                    if not parent:
                        continue
                    link_a = parent.find("a")
                    if not link_a:
                        continue
                        
                    title = link_a.get_text(strip=True)
                    raw_href = link_a.get("href", "")
                    href = decode_yahoo_url(raw_href)
                    snippet = div.get_text(strip=True)
                    
                    if not href or not title:
                        continue
                        
                    # Filter out Yahoo internal links and forums
                    lower_href = href.lower()
                    if "yahoo.com" in lower_href or "yahoo.co" in lower_href:
                        continue
                    if "reddit.com" in lower_href or "quora.com" in lower_href:
                        continue
                        
                    # Ensure we stay strictly in the context of VIT-AP and exclude other VIT campuses (Vellore, Chennai, Bhopal)
                    if "vit.ac.in" in lower_href and "vitap.ac.in" not in lower_href:
                        continue
                    if "vitbhopal.ac.in" in lower_href:
                        continue
                    if any(campus in lower_href for campus in ["vellore", "chennai", "bhopal"]) and not any(ap in lower_href for ap in ["vitap", "vit-ap"]):
                        continue
                        
                    results.append({
                        "title": title,
                        "content": snippet,
                        "source_url": href
                    })
                    if len(results) >= max_results:
                        break
    except Exception as e:
        print(f"[yahoo_search] Search error: {e}")
        
    print(f"[yahoo_search] Found {len(results)} results")
    return results


async def ddg_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Async search DuckDuckGo HTML and return a list of result dicts.
    Tight 1.5s timeout.
    """
    keyword_query = clean_search_query(query)
    search_query = keyword_query

    # Append "VIT AP" context for campus-specific queries
    if not check_is_general(query) and "vit" not in keyword_query.lower():
        search_query = f"{keyword_query} VIT AP"

    print(f"[ddg_search] Searching: '{search_query}' (original: '{query}')")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    ddg_url = "https://html.duckduckgo.com/html/"

    async with httpx.AsyncClient(timeout=1.5) as client:
        try:
            resp = await client.get(ddg_url, params={"q": search_query}, headers=headers)
            if resp.status_code == 200:
                results = _parse_ddg_html(resp.text, max_results)
                if results:
                    print(f"[ddg_search] Found {len(results)} results")
                    return results
        except Exception as e:
            print(f"[ddg_search] Search error/timeout: {e}")

    print("[ddg_search] Found 0 results")
    return []


async def web_search(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """
    Search DuckDuckGo and Yahoo Search in parallel to minimize latency.
    """
    import asyncio
    try:
        tasks = [ddg_search(query, max_results), yahoo_search(query, max_results)]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        ddg_res = results_list[0] if not isinstance(results_list[0], Exception) else []
        yahoo_res = results_list[1] if not isinstance(results_list[1], Exception) else []
        
        if ddg_res:
            return ddg_res
        return yahoo_res
    except Exception as e:
        print(f"[web_search] Parallel search error: {e}")
        return []
