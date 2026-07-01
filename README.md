<p align="center">
  <img src="./logo.svg" alt="vitap-UniOs Logo" width="550" />
</p>

<p align="center">
  <a href="https://github.com/hemasaivattikuti25/vitap-rag/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/hemasaivattikuti25/vitap-rag/ci.yml?branch=main&style=flat-square" alt="Build Status" />
  </a>
  <a href="https://github.com/hemasaivattikuti25/vitap-rag/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/hemasaivattikuti25/vitap-rag?style=flat-square" alt="License" />
  </a>
  <a href="https://github.com/hemasaivattikuti25/vitap-rag/stargazers">
    <img src="https://img.shields.io/github/stars/hemasaivattikuti25/vitap-rag?style=flat-square" alt="GitHub Stars" />
  </a>
  <a href="https://img.shields.io/badge/code%20style-black-000000.svg">
    <img src="https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square" alt="Code Style: Black" />
  </a>
</p>

---

**vitap-UniOs** is a production-grade, containerized campus information system and Retrieval-Augmented Generation (RAG) assistant designed for VIT-AP University. Built using **FastAPI**, **Qdrant**, and **Next.js 14**, it provides students with instant, reliable, and verified answers about university deans, fee structures, courses, placements, library hours, and campus events.

## 🏗️ Architecture Overview

The system utilizes a modular decoupled architecture containing a Next.js frontend, a FastAPI API gateway, and an automated background data ingestion pipeline.

```
                    +----------------------------------------+
                    |             Next.js Frontend           |
                    |     (Deployed on Vercel Edge Network)  |
                    +-------------------+--------------------+
                                        |
                                        | HTTPS / SSE (Streaming)
                                        v
                    +-------------------+--------------------+
                    |         FastAPI Production Server      |
                    |     (Hosted on Render Cloud Service)   |
                    +------+-----------+-----------+---------+
                           |           |           |
                           | gRPC      | In-Memory | HTTPS
                           v           v           v
                    +------+----+ +----+----+ +----+---------+
                    | Qdrant DB | | SQLite  | |   Groq LLM    |
                    | (Vector)  | | (Feed)  | | (Inference)   |
                    +-----------+ +---------+ +--------------+
```

### Key Technical Pillars

1. **Self-Healing Database Initialization**
   On startup, the FastAPI lifespan manager detects if the Qdrant database is empty or uninitialized. If so, it automatically triggers a fast, 4-second vector injection of hand-curated facts (`inject_all_facts.py`). This guarantees the assistant is functional immediately upon deployment, bypassing cold-start issues.

2. **Lightweight Vector Pipeline**
   To fit within Render's free tier RAM limit (512MB), we replaced heavy deep learning runtimes with **FastEmbed (ONNX)**. The embedding process uses `all-MiniLM-L6-v2` to generate 384-dimensional vectors locally in under 50ms per chunk without requiring a GPU or large system memory footprint.

3. **Hybrid Search & Term Boosting**
   Queries are routed to a hybrid search engine:
   - **Semantic Retrieve**: Finds contextual matches using cosine similarity on dense vectors.
   - **Lexical Retrieve**: Queries exact-match keywords across the Qdrant index.
   - **Local Reranker**: Ranks combined candidates using a lexical boost heuristic (giving weight to exact matches in document titles and contents).

4. **Robust Scraper with Fallback Protection**
   The crawler (`rebuild_index.py`) runs nightly at midnight IST via Playwright to fetch JS-rendered campus pages. It utilizes a 3-stage exponential backoff retry. If the live site is down or structural layout changes break the scraper, the system automatically falls back to the curated factual index, preventing service downtime.

5. **API Gateway Security**
   - **CORS Handling**: Preflight requests are intercepted with permissive regex rules for Vercel apps, resolving browser connectivity blocks natively.
   - **Rate Limiting**: Integrated `slowapi` middleware restricts the `/chat` route to `20/minute` per client IP.
   - **Input Guardrails**: Rejects prompt injection patterns before requesting LLM completions.

---

## 🛠️ Local Development & Quickstart

The easiest way to run the entire stack is using Docker Compose.

### Method 1: Containerized Environment (Docker Compose)

1. Clone the repository and copy the environment template:
   ```bash
   git clone https://github.com/hemasaivattikuti25/vitap-rag.git
   cd vitap-rag
   cp backend/.env.example backend/.env
   ```

2. Add your `GROQ_API_KEY` inside `backend/.env`.

3. Launch the containers:
   ```bash
   docker-compose up --build
   ```
   *This spins up the FastAPI backend at `localhost:8000`, the Next.js frontend at `localhost:3000`, and a local Qdrant instance at `localhost:6333`.*

---

### Method 2: Manual Developer Setup

#### 1. Backend Server
Ensure Python 3.11.4 is installed on your system.
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the fact injector to seed the local database
python inject_all_facts.py

# Launch the FastAPI development server
uvicorn main:app --reload --port 8000
```

#### 2. Frontend Server
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 📊 Environment Variable Reference

Configure these settings in your cloud provider's dashboard for production deployments.

### Backend (Render / Cloud Environment)

| Variable | Recommended Value | Purpose |
|---|---|---|
| `PYTHON_VERSION` | `3.11.4` | Enforces the correct Python container environment. |
| `QDRANT_URL` | `https://your-cluster.cloud.qdrant.io:6333` | Your Qdrant Cloud cluster URL (Leave empty/unset for local disk mode). |
| `QDRANT_API_KEY` | `your-qdrant-key` | Vector database authentication token. |
| `GROQ_API_KEY` | `gsk-your-groq-key` | Groq console key for fast LLaMA-3.1 model inference. |
| `ALLOWED_ORIGINS` | `https://vitap-rag.vercel.app` | Restricts API access to authorized domains (Regex allows preview Vercel links automatically). |

### Frontend (Vercel Environment)

| Variable | Value | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.onrender.com` | Points the web client to the live API gateway. |

---

## 🧪 Automated Testing & Evaluation

We maintain an evaluation script to run semantic-matching checks against typical campus queries. This test runs automatically in GitHub Actions CI to prevent search regressions.

```bash
cd backend
source venv/bin/activate
python evaluate_rag.py
```

The script evaluates retrieval accuracy across 7 core categories (Leadership, Fees, Admissions, Hostels, Transport, Libraries, and Placements) asserting term match and minimum similarity threshold scores.

---

## 🤝 Contributing

Contributions are welcome. Please refer to [CONTRIBUTING.md](CONTRIBUTING.md) for development policies, branching models, and PEP-8 code styling guidelines.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more details.
