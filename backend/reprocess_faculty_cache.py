#!/usr/bin/env python3
import os
import sys
import json
import urllib.parse
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from dotenv import load_dotenv

load_dotenv()

# Config
QDRANT_URL = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION = "campus_os"
MODEL_NAME = "all-MiniLM-L6-v2"
CACHE_FILE = "scraped_faculty_profiles.json"
DATA_FILE = "../data"

def parse_profile(content, source_url):
    lines = [l.strip() for l in content.split("\n") if l.strip()]
    
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
    if school == "Unknown" and source_url:
        parsed_url = urllib.parse.unquote(source_url)
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
    if "marychandini.y" in source_url.lower():
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
        "source_url": source_url
    }

def main():
    print("Reprocessing faculty cache file...")
    cache_path = os.path.join(os.path.dirname(__file__), CACHE_FILE)
    if not os.path.exists(cache_path):
        print(f"Error: {cache_path} does not exist.")
        sys.exit(1)
        
    with open(cache_path, "r") as f:
        profiles = json.load(f)
        
    updated_profiles = []
    for p in profiles:
        parsed = parse_profile(p["content"], p.get("source_url"))
        updated_profiles.append(parsed)
        
    # Write back to cache file
    with open(cache_path, "w") as f:
        json.dump(updated_profiles, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(updated_profiles)} updated profiles back to {CACHE_FILE}")

    # Generate markdown and update the data file
    data_filepath = os.path.join(os.path.dirname(__file__), DATA_FILE)
    if os.path.exists(data_filepath):
        with open(data_filepath, "r") as f:
            existing_content = f.read()
    else:
        existing_content = "# 🎓 VIT-AP University - Comprehensive Education, Faculty, & Facilities Directory\n"

    divider = "## 👩‍🏫 6. Teaching Faculty & Pedagogy"
    if divider in existing_content:
        base_part = existing_content.split(divider)[0]
        rest_part = existing_content.split(divider)[1]
        if "## 🏫 7. Campus Facilities & Infrastructure" in rest_part:
            facilities_part = "## 🏫 7. Campus Facilities & Infrastructure" + rest_part.split("## 🏫 7. Campus Facilities & Infrastructure")[-1]
        else:
            facilities_part = ""
    else:
        base_part = existing_content + "\n"
        facilities_part = ""

    faculty_by_school = {}
    for p in updated_profiles:
        sch = p["school"].strip()
        if sch == "Unknown" or not sch:
            sch = "Other / Administrative"
        if sch not in faculty_by_school:
            faculty_by_school[sch] = []
        faculty_by_school[sch].append(p)

    faculty_md = f"## 👩‍🏫 6. Teaching Faculty & Pedagogy\n\nVIT-AP employs highly qualified faculty members across its schools. Below is the detailed directory of all faculty members gathered from the official website:\n\n"
    for school_name, members in sorted(faculty_by_school.items()):
        faculty_md += f"### 📚 {school_name}\n\n"
        for m in sorted(members, key=lambda x: x["name"]):
            faculty_md += f"#### **{m['name']}**\n"
            faculty_md += f"*   **Designation:** {m['designation']}\n"
            faculty_md += f"*   **Specialisation:** {m['specialization']}\n"
            faculty_md += f"*   **Email:** {m['email']}\n"
            faculty_md += f"*   **Office Address:** {m['office_address']}\n"
            faculty_md += f"*   **Contact No:** {m['contact_no']}\n"
            faculty_md += f"*   **Details URL:** [{m['source_url']}]({m['source_url']})\n"
            
            c_lines = m["content"].split("\n")
            edu_idx = -1
            res_idx = -1
            for idx, line in enumerate(c_lines):
                if line.lower() == "education": edu_idx = idx
                if line.lower() == "research": res_idx = idx
            
            if edu_idx != -1:
                edu_text = " ".join([l.strip() for l in c_lines[edu_idx+1:edu_idx+8] if l.strip()])
                faculty_md += f"*   **Education:** {edu_text[:400]}\n"
            if res_idx != -1:
                res_text = " ".join([l.strip() for l in c_lines[res_idx+1:res_idx+8] if l.strip()])
                faculty_md += f"*   **Research & Specialization:** {res_text[:400]}\n"
            faculty_md += "\n"

    new_content = base_part + faculty_md + "\n" + facilities_part
    with open(data_filepath, "w") as f:
        f.write(new_content)
    print("Updated data file successfully!")

    # Embed & Upload to Qdrant
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
    for idx, p in enumerate(updated_profiles):
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
    main()
