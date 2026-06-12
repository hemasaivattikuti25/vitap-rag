"""
inject_all_facts.py
-------------------
Master fact-injection script. Runs EVERY rebuild cycle (called from
remove_boilerplate.py after re-indexing). Upserts verified, hand-curated
facts into Qdrant so the chatbot ALWAYS has accurate answers regardless
of whether the live website was parseable.

Covers:
  - B.Tech fee structure
  - Placement stats (₹93 LPA highest package)
  - FFCS class scheduling / V-TOP portal
  - Affidavit & student rules (live-fetched, then fallback to static)
  - VIT-AP key facts (NAAC, NIRF, NBA, established year, etc.)

Usage:
    ./venv/bin/python inject_all_facts.py
"""

import os, uuid, httpx
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from fastembed import TextEmbedding
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL     = os.getenv("QDRANT_URL", "local")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
COLLECTION     = "campus_os"
BACKEND_DIR    = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# ALL VERIFIED FACTS
# ─────────────────────────────────────────────────────────────────────────────
STATIC_FACTS = [

    # ── Fees ──────────────────────────────────────────────────────────────────
    {
        "title": "B.Tech Fee Structure — VIT-AP University",
        "source_url": "https://vitap.ac.in/fees-and-scholarships/",
        "category": "fees", "anchor": "btech_fees",
        "content": (
            "Official Fee Structure at VIT-AP University.\n\n"
            "1. B.Tech Tuition Fees (Per Annum) — based on VITEEE rank (5 categories):\n"
            "Group A (Biotechnology, Civil, EEE, Mechanical, etc.):\n"
            "  Cat 1: ₹1,73,000–₹1,76,000 | Cat 2: ₹2,70,000 | Cat 3: ₹3,43,000 "
            "| Cat 4: ₹4,05,000 | Cat 5: ₹4,50,000\n"
            "Group B (CSE, CSE specializations, ECE, etc.):\n"
            "  Cat 1: ₹1,95,000–₹1,98,000 | Cat 2: ₹3,07,000 | Cat 3: ₹4,05,000 "
            "| Cat 4: ₹4,48,000 | Cat 5: ₹4,93,000\n\n"
            "2. Other Programs (Per Annum):\n"
            "  BBA: ₹83,000 | B.Sc./Dual Degree Data Science: ₹58,000–₹90,000\n"
            "  M.Sc.: ₹60,000–₹80,000 | MBA: ₹3,53,000 | B.Com/B.A.: ₹50,000–₹70,000\n\n"
            "3. Hostel & Mess (Per Annum): ₹1,08,000–₹2,22,500 depending on room type.\n"
            "   One-time refundable caution deposit: ₹3,000 or ₹5,000."
        ),
    },

    # ── Placements ────────────────────────────────────────────────────────────
    {
        "title": "VIT-AP Placement Statistics — Highest Package & Key Figures",
        "source_url": "https://vitap.ac.in/cdc-statistics",
        "category": "placements", "anchor": "highest_package",
        "content": (
            "VIT-AP University Placement Statistics (Official CDC Data):\n\n"
            "• Highest Package: ₹93 LPA — highest salary ever offered to a VIT-AP student.\n"
            "• Average Package: ~₹8.5 LPA across all branches.\n"
            "• Placement Rate: 95%+ of eligible students placed.\n"
            "• Total Offers: 3,000+ offers from 300+ companies.\n"
            "• Dream Offers: above ₹5.5 LPA | Super Dream: above ₹10 LPA.\n\n"
            "Top Recruiters: Microsoft, Google, Amazon, Infosys, TCS, Wipro, "
            "Cognizant, Capgemini, Deloitte, IBM, Accenture, HCL, Zoho, Freshworks.\n\n"
            "The highest package at VIT-AP is ₹93 LPA."
        ),
    },
    {
        "title": "VIT-AP CDC — Career Development Centre Overview",
        "source_url": "https://vitap.ac.in/cdc-overview",
        "category": "placements", "anchor": "cdc_overview",
        "content": (
            "Career Development Centre (CDC) at VIT-AP University manages all placements.\n"
            "• Email: placement@vitap.ac.in | Phone: 08632370219\n"
            "• Organises campus drives, aptitude training, GD & interview prep.\n"
            "• Internships with PPO (Pre-Placement Offers) available.\n"
            "• Highest package: ₹93 LPA. Placement rate: 95%+. 300+ companies.\n"
            "• Statistics: https://vitap.ac.in/cdc-statistics"
        ),
    },

    # ── FFCS / Academics ──────────────────────────────────────────────────────
    {
        "title": "How to Schedule Classes at VIT-AP — FFCS (Fully Flexible Credit System)",
        "source_url": "https://vitap.ac.in/ffcs",
        "category": "academics", "anchor": "ffcs_scheduling",
        "content": (
            "VIT-AP uses FFCS (Fully Flexible Credit System). You design your own timetable.\n\n"
            "How to register/schedule courses:\n"
            "1. Log into V-TOP: https://vtop.vitap.ac.in\n"
            "2. Go to Academics → Course Registration → FFCS\n"
            "3. Select the subject (e.g., Operating Systems — CSE2005)\n"
            "4. Choose your preferred faculty/professor\n"
            "5. Choose a time slot (MWF or TT theory; separate lab slots)\n"
            "6. Confirm registration\n\n"
            "Key facts:\n"
            "• Registration opens by CGPA order — higher CGPA registers first\n"
            "• Seats fill in SECONDS — have 2–3 backup slot combos ready\n"
            "• OS (Operating Systems) is a 5th-semester course for CSE/ECE\n"
            "• Min credits/sem: 18 | Max: 27\n"
            "• Must maintain 75% attendance in every registered course\n"
            "• V-TOP also shows attendance, grades, exam schedule, and fee payment."
        ),
    },
    {
        "title": "VIT-AP V-TOP Portal — Student Portal for Registration & Academics",
        "source_url": "https://vtop.vitap.ac.in",
        "category": "academics", "anchor": "vtop_portal",
        "content": (
            "V-TOP (VIT-AP Technology Online Portal) — https://vtop.vitap.ac.in\n"
            "Official portal for all student academic activities at VIT-AP.\n\n"
            "Features:\n"
            "• FFCS Course Registration (schedule all semester courses)\n"
            "• Real-time attendance tracking by subject\n"
            "• Marks, CGPA, and grade cards\n"
            "• Exam hall ticket and schedule\n"
            "• Fee payment\n"
            "• Internship and placement registration via CDC\n\n"
            "To schedule any subject (OS, DBMS, CN, etc.):\n"
            "Login V-TOP → Academics → Course Registration → FFCS."
        ),
    },

    # ── University Key Facts ──────────────────────────────────────────────────
    {
        "title": "VIT-AP University — Key Facts & Accreditations",
        "source_url": "https://vitap.ac.in/",
        "category": "general", "anchor": "key_facts",
        "content": (
            "VIT-AP University (VIT-Andhra Pradesh) — Key Facts:\n\n"
            "• Full Name: VIT-AP University, Amaravati\n"
            "• Location: Beside AP Secretariat, Near Vijayawada, Andhra Pradesh — 522237\n"
            "• Established: 2017 (Deemed University status granted by UGC)\n"
            "• Part of the VIT Group (Vellore Institute of Technology)\n"
            "• NAAC Accredited\n"
            "• NBA Accredited programs\n"
            "• Ranked in NIRF (National Institutional Ranking Framework)\n"
            "• 8 Schools: SCOPE, SENSE, SMEC, SAS, SBST, VSB, VSL, VISH\n"
            "• 10,000+ students enrolled\n"
            "• 400+ faculty members\n"
            "• 65+ active clubs and chapters\n"
            "• International collaborations with 100+ universities worldwide\n"
            "• Placement: 95%+ rate | Highest package: ₹93 LPA\n"
            "• Website: https://vitap.ac.in | Admissions: VITEEE exam"
        ),
    },

    # ── Hostel ────────────────────────────────────────────────────────────────
    {
        "title": "VIT-AP Hostel Facilities & Fees",
        "source_url": "https://vitap.ac.in/hostels/",
        "category": "hostel", "anchor": "hostel_fees",
        "content": (
            "VIT-AP University Hostel Information:\n\n"
            "• Separate hostels for boys and girls — highly secure, 24×7 resident wardens.\n"
            "• Only VITians and authorized personnel allowed inside.\n"
            "• Facilities: cot, chair, study table, cupboard in each room.\n"
            "• Provision stores, laundry, and recreational spaces available.\n"
            "• Wi-Fi enabled throughout hostel premises.\n\n"
            "Hostel & Mess Fees (Per Annum):\n"
            "  ₹1,08,000 – ₹2,22,500 depending on room type (AC/Non-AC, "
            "single/double/multi-bed) and mess plan chosen.\n"
            "• Mess serves breakfast, lunch, snacks, and dinner.\n"
            "• Refundable caution deposit: ₹3,000 – ₹5,000 (one-time)."
        ),
    },

    # ── Committees ────────────────────────────────────────────────────────────
    {
        "title": "VIT-AP Anti-Ragging & Student Safety Committees",
        "source_url": "https://vitap.ac.in/arc",
        "category": "committees", "anchor": "committees",
        "content": (
            "VIT-AP University Student Safety & Governance Committees:\n\n"
            "• V-CHANCE (Student Grievance): https://vitap.ac.in/vchance\n"
            "• Anti-Ragging Committee (ARC): https://vitap.ac.in/arc\n"
            "  Strict zero-tolerance anti-ragging policy. Report: arc@vitap.ac.in\n"
            "• Internal Complaints Committee (ICC): https://vitap.ac.in/icc\n"
            "  Handles gender-based complaints under POSH Act.\n"
            "• University Disciplinary Committee (UDC): https://vitap.ac.in/udc\n"
            "• Grievance Redressal Committee (GRC): https://vitap.ac.in/grc\n\n"
            "All committees operate under UGC and statutory norms."
        ),
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# LIVE-FETCH AFFIDAVIT (with static fallback)
# ─────────────────────────────────────────────────────────────────────────────
AFFIDAVIT_STATIC_FALLBACK = (
    "VIT-AP University Affidavit & Student Rules:\n\n"
    "Before joining VIT-AP, students and parents must sign an affidavit agreeing to:\n"
    "• Anti-ragging rules — zero tolerance, strict legal action if violated.\n"
    "• Code of conduct — no harassment, substance use, or misconduct on campus.\n"
    "• Academic integrity — plagiarism and malpractice are punishable offenses.\n"
    "• Attendance — mandatory 75% per course or face debarment from exams.\n"
    "• Hostel rules — curfew timings, no outsiders, prior permission for outings.\n"
    "• Dress code — formal dress mandatory in academic zones.\n"
    "• Mobile policy — no phones in exam halls; restricted in labs.\n\n"
    "The affidavit is a legal document submitted online via V-TOP at the time of admission. "
    "Details: https://vitap.ac.in/affidavit"
)


def fetch_affidavit_live() -> str:
    """Try to fetch and parse the affidavit page; return text or empty string."""
    try:
        resp = httpx.get(
            "https://vitap.ac.in/affidavit",
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True, timeout=10.0
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Only use if we got meaningful content
        if len(text) > 300:
            return text[:3000]
    except Exception as e:
        print(f"  [affidavit] live fetch failed: {e}")
    return ""


def build_all_points(model: TextEmbedding) -> list[PointStruct]:
    facts = list(STATIC_FACTS)

    # Add affidavit (live or fallback)
    print("  [affidavit] Fetching live affidavit page...")
    affidavit_content = fetch_affidavit_live() or AFFIDAVIT_STATIC_FALLBACK
    facts.append({
        "title": "VIT-AP Affidavit & Student Code of Conduct",
        "source_url": "https://vitap.ac.in/affidavit",
        "category": "admissions", "anchor": "affidavit_rules",
        "content": affidavit_content,
    })

    texts = [f"{f['title']} {f['content']}" for f in facts]
    embeddings = list(model.embed(texts))

    points = []
    for fact, emb in zip(facts, embeddings):
        pid = str(uuid.uuid5(uuid.NAMESPACE_URL, fact["source_url"] + "#" + fact["anchor"]))
        points.append(PointStruct(
            id=pid, vector=emb.tolist(),
            payload={
                "title":      fact["title"],
                "content":    fact["content"],
                "source_url": fact["source_url"],
                "category":   fact.get("category", "general"),
            }
        ))
    return points


def get_clients():
    clients = []
    # Always write to local
    local_path = os.path.join(BACKEND_DIR, "local_qdrant")
    clients.append(("local", QdrantClient(path=local_path)))
    # Cloud if configured
    if QDRANT_URL and QDRANT_URL != "local" and QDRANT_URL.startswith("http"):
        clients.append(("cloud", QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, timeout=60.0)))
    return clients


def main():
    print("\n[inject_all_facts] Loading embedding model...")
    model = TextEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        cache_dir=os.path.join(BACKEND_DIR, "fastembed_cache")
    )

    print(f"[inject_all_facts] Building {len(STATIC_FACTS)+1} fact vectors...")
    points = build_all_points(model)

    for label, client in get_clients():
        try:
            client.upsert(collection_name=COLLECTION, points=points)
            print(f"[inject_all_facts] ✅ {len(points)} facts → {label} Qdrant")
        except Exception as e:
            print(f"[inject_all_facts] ❌ {label} failed: {e}")

    print("[inject_all_facts] Done.\n")


if __name__ == "__main__":
    main()
