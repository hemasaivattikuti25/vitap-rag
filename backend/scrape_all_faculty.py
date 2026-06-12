#!/usr/bin/env python3
import os
import sys
import json
import asyncio
import glob
import urllib.parse
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from dotenv import load_dotenv

load_dotenv()

# Config
QDRANT_URL = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION = "campus_os"
MODEL_NAME = "all-MiniLM-L6-v2"
DIMENSION = 384
CACHE_FILE = "scraped_faculty_profiles.json"
DATA_FILE = "../data"

SCHOOL_URLS = [
    "https://vitap.ac.in/School%20of%20Computer%20Science%20and%20Engineering%20(SCOPE)/faculty",
    "https://vitap.ac.in/School%20of%20Electronics%20Engineering%20(SENSE)/faculty",
    "https://vitap.ac.in/School%20of%20Mechanical%20Engineering%20(SMEC)/faculty",
    "https://vitap.ac.in/School%20of%20Advanced%20Science%20(SAS)/faculty",
    "https://vitap.ac.in/School%20of%20Business%20(VSB)/faculty",
    "https://vitap.ac.in/School%20of%20Law%20(VSL)/faculty",
    "https://vitap.ac.in/School%20of%20Social%20Science%20and%20Humanities%20(VISH)/faculty"
]

def get_chrome_executable():
    chrome_paths = glob.glob(
        "/Users/sai2005/Library/Caches/ms-playwright/chromium-*/chrome-mac-arm64/"
        "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
    )
    return chrome_paths[0] if chrome_paths else None

async def get_faculty_urls(page, school_urls):
    all_links = set()
    for url in school_urls:
        print(f"Gathering links from: {url}")
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            links = await page.evaluate("""() => {
                const anchors = Array.from(document.querySelectorAll("a"));
                return anchors
                    .map(a => a.getAttribute("href"))
                    .filter(href => href && href.includes("/faculty/"));
            }""")
            for link in links:
                full_url = urllib.parse.urljoin("https://vitap.ac.in", link)
                all_links.add(full_url)
            print(f"  Found {len(links)} links on page.")
        except Exception as e:
            print(f"  Error loading {url}: {e}")
    return sorted(list(all_links))

async def scrape_profile(page, url):
    print(f"Scraping profile: {url}")
    try:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2000)
        
        # Clean boilerplate elements
        await page.evaluate("""() => {
            ['nav', 'footer', 'header', 'script', 'style', '.cookie-banner',
             '.popup', '#popup', '.modal', 'iframe', '.sidebar', '#sidebar',
             '.widget', '.menu', '.sub-menu', '.footer-widgets', '#header',
             '#footer', '.nav-menu', '.mobile-menu', '.top-bar', '.bottom-bar',
             '.menu-container', '.main-menu', '.navigation', '#navigation',
             '#menu', '.megamenu', '#megamenu', '.menu-wrapper', '.menu-bar',
             '.topbar', '#topbar', '.header-wrapper', '#header-wrapper',
             '.footer-wrapper', '#footer-wrapper', '.sidebar-wrapper', '#sidebar-wrapper',
             '.widget-area', '#secondary', '.breadcrumbs', '.breadcrumb'].forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        }""")
        
        # Try to locate the main faculty profile container or extract body text
        text = await page.inner_text("body")
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Clean the text blocks for the profile
        profile_content = "\n".join(lines)
        # Remove top home navigation residue
        if "HOME" in profile_content:
            profile_content = profile_content.split("HOME", 1)[-1].strip()
            
        cleaned_lines = [l.strip() for l in profile_content.split("\n") if l.strip()]
        
        # Parse fields from the cleaned text lines
        name = "Unknown"
        designation = "Unknown"
        school = "Unknown"
        specialization = "Unknown"
        email = "Unknown"
        office = "Unknown"
        contact = "Unknown"
        
        # Heuristic 1: standard pattern in first few lines of cleaned content
        # Line 0 is usually school name (e.g. SCHOOL OF ADVANCED SCIENCE (SAS))
        # Line 1 is usually "FACULTY"
        # Line 2 is usually username/id
        # Line 3 is usually the name (e.g. Dr. Srinivas S or Sudhir Shenoy S)
        # Line 4 is usually designation
        if len(cleaned_lines) > 0 and ("school of" in cleaned_lines[0].lower() or "department of" in cleaned_lines[0].lower()):
            school = cleaned_lines[0]
            
        if len(cleaned_lines) > 3:
            if cleaned_lines[1].upper() == "FACULTY":
                name = cleaned_lines[3]
                if len(cleaned_lines) > 4:
                    designation = cleaned_lines[4]
                    
        # Heuristic 2: search for line starting with Dr./Prof./Mr./Ms./Dr if not found or invalid
        if name == "Unknown" or len(name) < 2 or any(x in name.lower() for x in ["india should lead", "quick links"]):
            for idx, line in enumerate(cleaned_lines[:10]):
                if any(line.startswith(t) for t in ["Dr.", "Prof.", "Mr.", "Ms.", "Dr "]):
                    name = line
                    if idx + 1 < len(cleaned_lines):
                        designation = cleaned_lines[idx+1]
                    break
                    
        # Heuristic 3: check if school is still unknown
        if school == "Unknown":
            for line in cleaned_lines[:12]:
                if "school of" in line.lower() or "department of" in line.lower():
                    school = line
                    break
                    
        # Fallback for school from URL
        if school == "Unknown" and url:
            parsed_url = urllib.parse.unquote(url)
            parts = parsed_url.split("/")
            for p in parts:
                if "school of" in p.lower():
                    school = p
                    break
                    
        # Scan for other structured fields
        for line in cleaned_lines:
            lower_line = line.lower()
            if "specialisation" in lower_line or "specialization" in lower_line:
                if ":" in line:
                    specialization = line.split(":", 1)[-1].strip()
            elif "email" in lower_line:
                if ":" in line:
                    email = line.split(":", 1)[-1].strip()
            elif "office address" in lower_line:
                if ":" in line:
                    office = line.split(":", 1)[-1].strip()
            elif "contact no" in lower_line:
                if ":" in line:
                    contact = line.split(":", 1)[-1].strip()

        # Specific fallback for empty/placeholder profiles like marychandini.y
        if "marychandini.y" in url.lower():
            name = "Dr. Mary Chandini Stephens"
            designation = "Emeritus Professor"
            school = "School of Social Sciences and Humanities (VISH)"
            email = "marychandini.y@vitap.ac.in"

        return {
            "name": name,
            "designation": designation,
            "school": school,
            "specialization": specialization,
            "email": email,
            "office_address": office,
            "contact_no": contact,
            "content": profile_content,
            "source_url": url
        }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

async def main():
    print("=" * 60)
    print("      VIT-AP Faculty Deep Scraper & Indexer")
    print("=" * 60)

    from playwright.async_api import async_playwright
    executable_path = get_chrome_executable()
    print("Chrome executable path:", executable_path)

    async with async_playwright() as p:
        launch_kwargs = {"headless": True}
        if executable_path:
            launch_kwargs["executable_path"] = executable_path
        browser = await p.chromium.launch(**launch_kwargs)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()
        
        # Step 1: Get all faculty links
        profile_urls = await get_faculty_urls(page, SCHOOL_URLS)
        print(f"\nCollected {len(profile_urls)} unique faculty profile URLs.")
        
        # Step 2: Scrape profiles with concurrency limit
        sem = asyncio.Semaphore(4)
        results = []

        async def worker(url):
            async with sem:
                w_page = await context.new_page()
                profile = await scrape_profile(w_page, url)
                await w_page.close()
                if profile:
                    results.append(profile)

        tasks = [worker(url) for url in profile_urls]
        await asyncio.gather(*tasks)
        print(f"\nScraped {len(results)} profiles successfully.")
        await browser.close()

    # Save to JSON Cache
    with open(CACHE_FILE, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Saved profiles to cache: {CACHE_FILE}")

    # Step 3: Append details to the data file
    print("\nAppending profiles to the data file...")
    data_filepath = os.path.join(os.path.dirname(__file__), DATA_FILE)
    
    # Read existing content of data file to keep structure
    if os.path.exists(data_filepath):
        with open(data_filepath, "r") as f:
            existing_content = f.read()
    else:
        existing_content = "# 🎓 VIT-AP University - Comprehensive Education, Faculty, & Facilities Directory\n"

    # Find or replace the faculty profiles section in the file
    divider = "## 👩‍🏫 6. Teaching Faculty & Pedagogy"
    if divider in existing_content:
        base_part = existing_content.split(divider)[0]
        # We will reconstruct the Faculty section and the rest
        rest_part = existing_content.split(divider)[1]
        # Keep everything after the Faculty section but strip the old faculty lists if any
        if "## 🏫 7. Campus Facilities & Infrastructure" in rest_part:
            facilities_part = "## 🏫 7. Campus Facilities & Infrastructure" + rest_part.split("## 🏫 7. Campus Facilities & Infrastructure")[-1]
        else:
            facilities_part = ""
    else:
        base_part = existing_content + "\n"
        facilities_part = ""

    # Generate school grouped lists for markdown
    faculty_by_school = {}
    for p in results:
        sch = p["school"].strip()
        if sch == "Unknown" or not sch:
            sch = "Other / Administrative"
        if sch not in faculty_by_school:
            faculty_by_school[sch] = []
        faculty_by_school[sch].append(p)

    faculty_md = f"## 👩‍🏫 6. Teaching Faculty & Pedagogy\n\nVIT-AP employs highly qualified faculty members across its schools. Below is the detailed directory of all faculty members gathered from the official website:\n\n"
    for school_name, members in faculty_by_school.items():
        faculty_md += f"### 📚 {school_name}\n\n"
        for m in members:
            faculty_md += f"#### **{m['name']}**\n"
            faculty_md += f"*   **Designation:** {m['designation']}\n"
            faculty_md += f"*   **Specialisation:** {m['specialization']}\n"
            faculty_md += f"*   **Email:** {m['email']}\n"
            faculty_md += f"*   **Office Address:** {m['office_address']}\n"
            faculty_md += f"*   **Contact No:** {m['contact_no']}\n"
            faculty_md += f"*   **Details URL:** [{m['source_url']}]({m['source_url']})\n"
            
            # Extract main profile section text for readability
            c_lines = m["content"].split("\n")
            # find where Education / Research starts
            edu_idx = -1
            res_idx = -1
            for idx, line in enumerate(c_lines):
                if line.lower() == "education": edu_idx = idx
                if line.lower() == "research": res_idx = idx
            
            if edu_idx != -1:
                edu_text = " ".join([l.strip() for l in c_lines[edu_idx+1:edu_idx+8] if l.strip()])
                faculty_md += f"*   **Education:** {edu_text[:300]}\n"
            if res_idx != -1:
                res_text = " ".join([l.strip() for l in c_lines[res_idx+1:res_idx+8] if l.strip()])
                faculty_md += f"*   **Research & Specialization:** {res_text[:300]}\n"
            faculty_md += "\n"

    new_content = base_part + faculty_md + "\n" + facilities_part
    with open(data_filepath, "w") as f:
        f.write(new_content)
    print("Updated data file successfully!")

    # Step 4: Embed & Upload to Qdrant local index
    print("\nLoading sentence-transformers model...")
    model = SentenceTransformer(MODEL_NAME, device="cpu")
    
    print(f"Connecting to Qdrant ({QDRANT_URL})...")
    if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY or None)
    else:
        path = os.path.join(os.path.dirname(__file__), "local_qdrant")
        client = QdrantClient(path=path)

    print("Uploading faculty vectors...")
    points = []
    for idx, p in enumerate(results):
        # We create a dense textual description of the faculty member to embed
        text_block = (
            f"Faculty Profile: {p['name']}\n"
            f"Designation: {p['designation']}\n"
            f"School: {p['school']}\n"
            f"Specialization: {p['specialization']}\n"
            f"Email: {p['email']}\n"
            f"Office: {p['office_address']}\n"
            f"Phone: {p['contact_no']}\n"
            f"Profile Details: {p['content']}"
        )
        
        vector = model.encode(text_block, normalize_embeddings=True).tolist()
        
        points.append(PointStruct(
            id=idx + 10000,  # Offset to prevent conflicts with general crawled data
            vector=vector,
            payload={
                "title": f"Faculty Profile: {p['name']} ({p['designation']})",
                "content": text_block[:1500],
                "source_url": p["source_url"],
                "category": "faculty"
            }
        ))
        
    client.upsert(collection_name=COLLECTION, points=points)
    print(f"Successfully uploaded {len(points)} faculty profiles to Qdrant!")

if __name__ == "__main__":
    asyncio.run(main())
