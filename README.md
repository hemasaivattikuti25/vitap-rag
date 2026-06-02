# CampusOS (Mithra Campus) MVP

An intelligent campus assistant for VIT-AP built using a Retrieval Augmented Generation (RAG) architecture.

## Tech Stack
- **Frontend**: Next.js 14, Tailwind CSS, Lucide React
- **Backend**: FastAPI, Python
- **Database**: Supabase (PostgreSQL)
- **Vector Database**: Qdrant (Local via Docker)
- **AI/LLM**: Google Gemini API

## Prerequisites
- Node.js (v18+)
- Python 3.10+
- Docker & Docker Compose
- Supabase Account
- Google Gemini API Key

## Setup Instructions

### 1. Database & Vector DB Setup
1. Create a Supabase project. In your database, create a `sources` table with the following schema:
   - `id` (uuid, primary key)
   - `title` (text)
   - `type` (text)
   - `content` (text)
   - `source_url` (text)
   - `updated_at` (timestamp)
2. Start the local Qdrant vector database:
   ```bash
   docker-compose up -d
   ```

### 2. Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install fastapi uvicorn supabase qdrant-client google-generativeai beautifulsoup4 requests pydantic python-dotenv
   ```
4. Update the `backend/.env` file with your credentials:
   - `SUPABASE_URL` and `SUPABASE_KEY`
   - `GEMINI_API_KEY`
5. Run the crawler to scrape VIT-AP and populate your Supabase and Qdrant databases:
   ```bash
   python crawler/pipeline.py
   ```
6. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### 3. Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```

### Usage
Open [http://localhost:3000](http://localhost:3000) in your browser. You can navigate the Clubs, Events, and interact with the AI Chat assistant which uses real scraped data from the VIT-AP portal!
