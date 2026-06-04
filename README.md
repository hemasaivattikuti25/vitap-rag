#  vitap-UniOs — Campus Platform for VIT-AP

<p align="center">
  <img src="frontend/public/logo.png" alt="vitap-UniOs Logo" width="100" height="100" style="border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);" />
</p>

An intelligent, premium university OS platform for VIT-AP. It features a real-time scraping pipeline, categorised clubs and events databases, and an advanced **Retrieval-Augmented Generation (RAG)** AI Chat assistant that answers student queries about courses, hostels, academic calendars, and official affidavits.

Developed by **Hemasai Vattikuti**. Powered by **Groq** + **Qdrant**.

---

## 🚀 Key Features

* **🤖 RAG AI Assistant:** Context-aware chatbot powered by Groq (LLaMA-3) and a semantic Qdrant vector database. It searches official VIT-AP documents, course structures, and student guidelines.
* **📰 Real-Time Campus Feed:** An automated background web-crawling daemon that runs every 30 minutes to scrape announcements, news, and opportunities from VIT-AP portals.
* **🏛️ Categorised Clubs Board:** Dynamic dashboard featuring 70+ student clubs and chapters, classified automatically (Technical, Cultural, Sports, etc.) using text heuristics.
* **📅 Interactive Events Board:** Live campus events tracker providing dates, venues, descriptions, and official registration links.
* **📱 Progressive Web App (PWA):** Installable on iOS & Android directly from mobile browsers with a fully optimized mobile-first layout.

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
                        |  FastAPI / Render Cloud |
                        +------+-----------+------+
                               |           |
                               v           v
            +------------------+--+     +--+------------------+
            |  Qdrant Vector DB   |     | SQLite Mock Database|
            |  (Local on-disk)    |     | (local_supabase.db) |
            +---------------------+     +---------------------+
```

* **Frontend:** Next.js 14 (App Router), Vanilla CSS, responsive layouts using `100dvh` (Dynamic Viewports).
* **Backend:** FastAPI (Python 3.11), Uvicorn.
* **Vector Database:** Qdrant (Runs locally on-disk in `local_qdrant/` — **no Docker/key required**).
* **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors).
* **Mock Database:** SQLite (`local_supabase.db`) wrapped in a Supabase Mock SDK for local-first zero-credentials compatibility.
* **AI Engine:** Groq API (LLaMA 3 70B & 8B models with automated failovers).

---

## ⚙️ Local Development Setup

### 1. Prerequisites
* **Node.js** (v18+)
* **Python** (v3.10+)
* A **Groq API Key** (Get one for free at [console.groq.com](https://console.groq.com))

---

### 2. Backend Setup
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
4. Create a `backend/.env` file with the following variables:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   QDRANT_URL=local
   SUPABASE_URL=mock
   SUPABASE_KEY=mock
   ```
5. Run the background index builder script (downloads embeddings model, scrapes sites, and builds vector index):
   ```bash
   python rebuild_index.py
   ```
6. Start the FastAPI development server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

The backend API will be running at [http://localhost:8000](http://localhost:8000).

---

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```

Open [http://localhost:3000](http://localhost:3000) in your browser. The app is ready!

---

## 🌐 Cloud Deployment (Vercel + Render)

### 1. Backend (Render)
You can deploy the FastAPI server to **Render** using the provided `render.yaml` blueprint:
1. Connect your repository to Render.
2. Click **New** → **Blueprint** and select this repo.
3. Configure the following environment variables on the Render dashboard:
   * `GROQ_API_KEY` (Your API key)
   * `QDRANT_URL` (Set to `local`)
   * `SUPABASE_URL` (Set to `mock`)
   * `SUPABASE_KEY` (Set to `mock`)
4. Deploy the service. Take note of the web service URL (e.g. `https://vitap-unios.onrender.com`).

### 2. Frontend (Vercel)
1. Import your project into **Vercel**.
2. Go to **Project Settings** → **Environment Variables**.
3. Add a new variable:
   * **Key:** `NEXT_PUBLIC_API_URL`
   * **Value:** `https://your-backend-name.onrender.com` (Your Render URL)
4. Trigger a build. Vercel will optimize and host the client app.

---

## 📂 Project Structure

```
vitap-UniOs/
├── backend/
│   ├── api/             # FastAPI routers & endpoints
│   ├── crawler/         # Async crawler scripts & web scrapers
│   ├── db/              # In-memory feed store & SQLite supabase mock
│   ├── models/          # Pydantic schemas
│   ├── rag/             # Qdrant retrievers & Groq generator streams
│   ├── main.py          # Entry point (initializes background crawler daemon)
│   ├── rebuild_index.py # Scrapes website and builds Qdrant local files
│   └── render.yaml      # Render blueprint configuration
└── frontend/
    ├── public/          # Assets (logos, PWAs, banner images)
    └── src/app/         # Next.js pages (Chat, Clubs, Events dashboards)
```

---

Developed with ❤️ by **Hemasai Vattikuti**. Feel free to star this repository if you found it helpful!
