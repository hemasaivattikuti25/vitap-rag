# 🎓 vitap-UniOs — Campus Platform for VIT-AP

<p align="center">
  <img src="frontend/public/logo.png" alt="vitap-UniOs Logo" width="100" height="100" style="border-radius: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);" />
</p>

<p align="center">
  <a href="https://github.com/hemasaivattikuti25/vitap-rag/actions/workflows/ci.yml">
    <img src="https://github.com/hemasaivattikuti25/vitap-rag/actions/workflows/ci.yml/badge.svg" alt="CI Build Status" />
  </a>
  <a href="https://github.com/hemasaivattikuti25/vitap-rag/stargazers">
    <img src="https://img.shields.io/github/stars/hemasaivattikuti25/vitap-rag?color=yellow&style=flat-square" alt="GitHub Stars" />
  </a>
  <a href="https://github.com/hemasaivattikuti25/vitap-rag/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/hemasaivattikuti25/vitap-rag?color=blue&style=flat-square" alt="License" />
  </a>
</p>

An intelligent, premium university OS platform for VIT-AP. It features a real-time scraping pipeline, categorised clubs and events databases, and an advanced **Retrieval-Augmented Generation (RAG)** AI Chat assistant that answers student queries about courses, hostels, academic calendars, and official affidavits.

Developed by **Hemasai Vattikuti**. Powered by **Groq** + **Qdrant**.

---

## 🚀 Key Features

* **🤖 Hybrid RAG AI Assistant:** Context-aware chatbot utilizing keyword-augmented vector search (Qdrant) and LLM streaming (Groq). Features a local lexical-semantic reranker for extreme precision.
* **🛡️ Security & Guardrails:** Built-in rate limiting (max 20 requests/minute via `slowapi`) and input filters to block prompt injection or malicious attempts.
* **📈 Automated RAG Evaluation:** A local evaluation suite (`evaluate_rag.py`) that tests retrieval accuracy on typical queries against a ground-truth dataset.
* **📰 Real-Time Campus Feed:** Automated background crawler daemon running every 30 minutes to capture live campus announcements and opportunities.
* **🏛️ Categorised Clubs Board:** Dynamic dashboard featuring 70+ student clubs and chapters, classified automatically (Technical, Cultural, Sports, etc.).
* **📱 Progressive Web App (PWA):** Installable on iOS & Android directly from mobile browsers.

---

## 🛠️ Tech Stack & Architecture

```
                 +----------------------------------------+
                 |          User Browser / PWA            |
                 +-------------------+--------------------+
                                     |
                                     v
                        +------------+------------+
                        |  Next.js 14 / Vercel    |
                        +------------+------------+
                                     |
                                     v
                        +------------+------------+
                        |  FastAPI / Render Cloud | ── [Rate Limiter & Guardrails]
                        +------+-----------+------+
                               |           |
                               v           v
            +------------------+--+     +--+------------------+
            |  Qdrant Vector DB   |     | SQLite Mock Database|
            |  (Local/Cloud Sync) |     | (local_supabase.db) |
            +---------------------+     +---------------------+
```

* **Frontend:** Next.js 14 (App Router), Vanilla CSS, responsive dynamic viewports.
* **Backend:** FastAPI (Python 3.11), Uvicorn, SlowAPI.
* **Vector DB:** Qdrant Cloud + Local disk failover fallback.
* **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors).
* **AI Engine:** Groq API (LLaMA 3.1 70B & 8B models).

---

## 🐳 Quick 1-Click Setup (Docker Compose)

Get the entire stack (Next.js, FastAPI, Qdrant DB) running in a single command:

1. Clone the repository and configure your environment:
   ```bash
   cp backend/.env.example backend/.env
   # Add your GROQ_API_KEY inside backend/.env
   ```
2. Run Docker Compose:
   ```bash
   docker-compose up --build
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your browser!

---

## ⚙️ Manual Local Development Setup

### 1. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `backend/.env` file:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   QDRANT_URL=local
   SUPABASE_URL=mock
   SUPABASE_KEY=mock
   ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
   ```
5. Run the background index builder script (scrapes pages and builds vector index):
   ```bash
   python rebuild_index.py
   ```
6. Start the development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
2. Open [http://localhost:3000](http://localhost:3000).

---

## 🧪 Testing & Evaluation

We run a local evaluation suite to ensure that search retrieval is accurate and relevant.

To run the RAG evaluator:
```bash
cd backend
python evaluate_rag.py
```

This runs a 7-query ground-truth verification suite, checking cosine similarity, title matching, and keyword overlap.

---

## 🤝 Contributing

Contributions make the open-source community amazing. Please read our [CONTRIBUTING.md](CONTRIBUTING.md) to get started.

Developed with ❤️ by **Hemasai Vattikuti**. Feel free to star this repository!
