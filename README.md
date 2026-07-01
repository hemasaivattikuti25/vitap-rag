# vitap-UniOs — Campus Platform for VIT-AP

An intelligent, production-grade campus information assistant and RAG pipeline for VIT-AP University. This repository contains the unified architecture for scraping live campus portals, indexing structured facts in Qdrant, protecting endpoints via rate limiting, and delivering context-aware answers to student queries.

---

## 🏗️ System Architecture

The platform is designed around a modular, three-tier architecture:

```
                    +----------------------------------------+
                    |           Next.js 14 Web App           |
                    +-------------------+--------------------+
                                        |
                                        v  [CORS Restricted API]
                    +-------------------+--------------------+
                    |        FastAPI Production Server       |
                    |    (Rate Limiting & Safety Filters)    |
                    +------+-----------+-----------+---------+
                           |           |           |
                           v           v           v
                  +--------+--+  +-----+---+  +----+---------+
                  | Qdrant DB |  | SQLite  |  |  Groq LLaMA  |
                  | (Hybrid)  |  | (Mock)  |  |  Inference   |
                  +-----------+  +---------+  +--------------+
```

### 1. Ingestion & In-Memory Pipeline (`crawler/`, `rebuild_index.py`)
- Automated background scrapers that run at midnight IST to scrape 65+ vitap.ac.in pages using Playwright (resilient to JS rendering with 3× exponential backoff retries).
- Cleans and structures raw HTML, extracting page blocks, lists, and tables while discarding header/footer boilerplate.
- Normalizes and synchronizes verified static anchors (SCOPE/SENSE deans, hostels, sports, healthcare, transport) as the baseline "source of truth".

### 2. Retrieval-Augmented Generation (`rag/`)
- **Hybrid Retrieval**: Combines semantic dense vector search (384-dimensional embeddings via FastEmbed ONNX runtime) with exact-match lexical Qdrant scroll queries.
- **Lexical-Semantic Reranker**: Locally re-scores candidate documents in Python, weighting keyword match frequency in the title and content to resolve semantic ambiguity for specific campus entities.
- **Groq Inference**: Streamed completions using Groq's high-speed async client (LLaMA 3.1 70B & 8B) for fast response times.

### 3. API Layer & Safety Gateway (`main.py`, `api/`)
- Protected chat streaming endpoint (`/api/chat`) implementing `slowapi` rate limiting (20 requests/minute per client IP).
- Input guardrails checking for prompt injection keywords and malicious overrides.
- Persistent user feedback endpoint (`/api/chat/feedback`) logging ratings to `feedback_logs.jsonl` for continuous quality updates.

---

## 📊 Environment Configuration (Render & Vercel)

Ensure these variables are configured correctly in your production host dashboard.

### Backend (Render Cloud)
| Variable | Value/Description | Purpose |
|---|---|---|
| `PYTHON_VERSION` | `3.11.4` | Enforces the correct Python runtime |
| `ALLOWED_ORIGINS` | `https://vitap-rag.vercel.app` | Restricts CORS to the production frontend domain |
| `QDRANT_URL` | `https://xxxx.cloud.qdrant.io:6333` | Production Qdrant Cloud cluster endpoint |
| `QDRANT_API_KEY` | `your_qdrant_cloud_api_key` | Authentication key for production vector DB |
| `GROQ_API_KEY` | `gsk_your_groq_production_key` | Key for LLaMA-3.1 inference model |
| `SUPABASE_URL` | `mock` | Mock Supabase configuration for local-first testing |
| `SUPABASE_KEY` | `mock` | Mock Supabase key |

### Frontend (Vercel)
| Variable | Value/Description | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://campusos-backend.onrender.com` | Production API gateway endpoint |

---

## 🐳 Deployment & Local Setup

### Unified Container Build (Docker Compose)
To run the Next.js client, FastAPI server, and a local Qdrant instance together in a isolated container environment:
```bash
# 1. Clone the project and duplicate the configuration template
cp backend/.env.example backend/.env

# 2. Add your Groq API key inside backend/.env, then launch:
docker-compose up --build
```
Access the application dashboard at `http://localhost:3000`.

### Manual Developer Build (Python Venv)
1. **Backend Configuration**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Run the crawler and index builder
   python rebuild_index.py --force
   
   # Run the local server
   uvicorn main:app --reload --port 8000
   ```
2. **Frontend Configuration**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

---

## 🧪 RAG Evaluation & Ingestion Tests

To ensure accurate retrieval and prevent regressions when updating model anchors or crawler layouts, we maintain a local evaluation suite:

```bash
cd backend
python evaluate_rag.py
```

The evaluation script validates search retrieval across 7 standard categories (SCOPE Dean, course scheduling, placement packages, library hours, banking locations, hostel fees, and SENSE Dean) against a predefined ground-truth dataset, asserting exact term occurrence and minimum cosine similarity thresholds.

---

## 🤝 Contributing

Developer contributions are welcome. Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for details on formatting, branching, and pull request steps.
