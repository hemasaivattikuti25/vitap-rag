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

    # ── University Deans & Leadership ─────────────────────────────────────────
    {
        "title": "VIT-AP Deans & School Leadership — All Schools",
        "source_url": "https://vitap.ac.in/allschools/",
        "category": "academics", "anchor": "deans_leadership",
        "content": (
            "VIT-AP University — Deans and School Leadership:\n\n"
            "University-Level Deans:\n"
            "• Dean of Academics: Dr. Madhusudhana Rao N\n"
            "• Dean of Academic Research: Dr. M. Venkata Rajanikanth "
            "(heads PhD, SPORIC activities, and URE research projects)\n\n"
            "School Deans:\n"
            "• SCOPE Dean (School of Computer Science & Engineering): Dr. Sudhakar Ilango\n"
            "• SENSE Dean (School of Electronics Engineering): Dr. Y. V. Pavan Kumar\n"
            "• SAS Dean (School of Advanced Sciences): Dr. Srinivas S\n"
            "• SMEC Dean (School of Mechanical Engineering): Dr. Dilipkumar Mohanty\n"
            "• VSL Dean (School of Law): Dr. Benarji Chakka\n"
            "• VSB Dean (School of Business): Dr. Arunkumar Sivakumar\n\n"
            "The Dean of SCOPE is Dr. Sudhakar Ilango.\n"
            "The Dean of SENSE is Dr. Y. V. Pavan Kumar.\n"
            "The Dean of SAS is Dr. Srinivas S.\n"
            "The Dean of SMEC is Dr. Dilipkumar Mohanty."
        ),
    },

    # ── SCOPE School ──────────────────────────────────────────────────────────
    {
        "title": "SCOPE — School of Computer Science and Engineering at VIT-AP",
        "source_url": "https://vitap.ac.in/allschools/SCOPE",
        "category": "academics", "anchor": "scope_school",
        "content": (
            "School of Computer Science and Engineering (SCOPE) — VIT-AP University:\n\n"
            "Dean: Dr. Sudhakar Ilango\n\n"
            "Programs offered:\n"
            "• B.Tech CSE | B.Tech CSE (AI & ML) | B.Tech CSE (Blockchain)\n"
            "• B.Tech CSE (Cyber Security) | B.Tech CSE (Data Analytics)\n"
            "• B.Tech CSE (Software Engineering) | B.Tech CSBS (with TCS)\n"
            "• Integrated M.Tech CSE (5-year) | M.Tech CSE | PhD CSE\n\n"
            "SCOPE focuses on high-demand CS disciplines with modern labs and "
            "industry-aligned curriculum. Engineering Clinics and URE projects "
            "are part of the curriculum."
        ),
    },

    # ── SENSE School ──────────────────────────────────────────────────────────
    {
        "title": "SENSE — School of Electronics Engineering at VIT-AP",
        "source_url": "https://vitap.ac.in/allschools/SENSE",
        "category": "academics", "anchor": "sense_school",
        "content": (
            "School of Electronics Engineering (SENSE) — VIT-AP University:\n\n"
            "Dean: Dr. Y. V. Pavan Kumar\n\n"
            "Programs offered:\n"
            "• B.Tech ECE | B.Tech ECE (VLSI) | B.Tech ECE (Embedded Systems)\n"
            "• B.Tech EEE | B.Tech ECM\n"
            "• Integrated M.Tech VLSI Design (5-year) | M.Tech VLSI | PhD Electronics\n\n"
            "SENSE prepares students for VLSI design, communications, signal processing, "
            "and embedded systems careers."
        ),
    },

    # ── Facilities ────────────────────────────────────────────────────────────
    {
        "title": "VIT-AP Campus Facilities — Infrastructure, Labs, Transport, Healthcare",
        "source_url": "https://vitap.ac.in/infrastructure",
        "category": "facilities", "anchor": "all_facilities",
        "content": (
            "VIT-AP University Campus Facilities:\n\n"
            "INFRASTRUCTURE:\n"
            "• State-of-the-art academic blocks with smart classrooms.\n"
            "• High-speed Wi-Fi across the entire campus.\n"
            "• 24×7 power backup via generators and solar panels.\n"
            "• Fully equipped auditorium and seminar halls.\n\n"
            "LABORATORIES:\n"
            "• 50+ specialized labs: Computing, VLSI, Robotics, Embedded Systems,\n"
            "  Biotech, Chemistry, Physics, Mechanical, Civil, and more.\n"
            "• Each lab has modern equipment updated per industry standards.\n"
            "• Labs are accessible to students for project and research work.\n\n"
            "TRANSPORT:\n"
            "• VIT-AP provides bus transportation to and from Vijayawada, Guntur,\n"
            "  and surrounding areas.\n"
            "• Buses run on fixed routes daily for day scholars.\n"
            "• Bus pass registration done through V-TOP portal.\n\n"
            "HEALTHCARE / MEDICAL CENTER:\n"
            "• On-campus Health Center (Medical Center) with qualified doctors and nurses.\n"
            "• 24×7 ambulance facility available for emergencies.\n"
            "• First aid available in every hostel block.\n"
            "• Regular health camps and blood donation drives organized.\n\n"
            "BANK & ATM:\n"
            "• State Bank of India (SBI) branch and ATM on campus.\n"
            "• Additional ATMs from multiple banks available.\n\n"
            "CAFETERIA:\n"
            "• Multiple food courts and cafeterias serving vegetarian and\n"
            "  non-vegetarian meals at subsidized rates.\n"
            "• Brands and outlets: various cuisine options available.\n\n"
            "GUEST HOUSE:\n"
            "• Fully furnished guest house for visiting faculty, parents, and delegates.\n\n"
            "LIBRARY:\n"
            "• Digital and physical library with 50,000+ books and journals.\n"
            "• Access to online databases: IEEE Xplore, Springer, Elsevier, NPTEL.\n"
            "• Open 8 AM – 10 PM on working days."
        ),
    },

    # ── Sports ────────────────────────────────────────────────────────────────
    {
        "title": "VIT-AP Sports Facilities",
        "source_url": "https://vitap.ac.in/sports/",
        "category": "sports", "anchor": "sports_facilities",
        "content": (
            "VIT-AP University Sports Facilities:\n\n"
            "• Cricket ground | Football/Soccer field | Basketball courts\n"
            "• Volleyball courts | Badminton courts (indoor)\n"
            "• Table Tennis | Chess | Carrom\n"
            "• Swimming pool\n"
            "• Gymnasium / Fitness center\n"
            "• Athletics track\n\n"
            "VIT-AP participates in inter-university tournaments and South Zone games. "
            "Sports scholarships available for outstanding athletes. Sports Director "
            "manages all sports activities on campus."
        ),
    },

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
            "• Min credits/sem: 18 | Max: 27 | Must maintain 75% attendance."
        ),
    },
    {
        "title": "VIT-AP V-TOP Portal — Student Portal for Registration & Academics",
        "source_url": "https://vtop.vitap.ac.in",
        "category": "academics", "anchor": "vtop_portal",
        "content": (
            "V-TOP (VIT-AP Technology Online Portal) — https://vtop.vitap.ac.in\n"
            "Official portal for all student academic activities at VIT-AP.\n\n"
            "Features: FFCS Course Registration, attendance tracking, marks/CGPA, "
            "exam hall ticket, fee payment, internship & placement registration.\n\n"
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
            "• NAAC Accredited | NBA Accredited programs | NIRF Ranked\n"
            "• 8 Schools: SCOPE, SENSE, SMEC, SAS, SBST, VSB, VSL, VISH\n"
            "• 10,000+ students | 400+ faculty | 65+ clubs | 100+ global university ties\n"
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
            "• Facilities per room: cot, chair, study table, cupboard. Wi-Fi enabled.\n"
            "• Provision stores, laundry, and recreational spaces available.\n\n"
            "Hostel & Mess Fees (Per Annum):\n"
            "  ₹1,08,000 – ₹2,22,500 depending on room type (AC/Non-AC, "
            "single/double/multi-bed) and mess plan.\n"
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
