#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# vitap-UniOs Dev Container Setup Script
# Runs once after the container is created. Sets up backend + frontend.
# ─────────────────────────────────────────────────────────────────────────────
set -e

echo "════════════════════════════════════════════════"
echo "  vitap-UniOs: Setting up development environment"
echo "════════════════════════════════════════════════"

# ── 1. Backend (Python) ────────────────────────────────────────────────────
echo ""
echo "▶ Installing Python backend dependencies..."
cd /workspaces/collgeportal/backend
python -m pip install --upgrade pip
pip install -r requirements.txt

# ── 2. Download embedding model so first boot is instant ──────────────────
echo ""
echo "▶ Pre-downloading FastEmbed model weights..."
python download_model.py

# ── 3. Seed the local vector database ────────────────────────────────────
echo ""
echo "▶ Seeding local Qdrant database with VIT-AP facts..."
python inject_all_facts.py

# ── 4. Frontend (Node.js) ─────────────────────────────────────────────────
echo ""
echo "▶ Installing Node.js frontend dependencies..."
cd /workspaces/collgeportal/frontend
npm install

# ── 5. Copy .env example for developer ───────────────────────────────────
echo ""
if [ ! -f /workspaces/collgeportal/backend/.env ]; then
  echo "▶ Creating .env from example (add your GROQ_API_KEY)..."
  cat > /workspaces/collgeportal/backend/.env << 'EOF'
# ── Paste your Groq API key here (free at console.groq.com) ──
GROQ_API_KEY=your-groq-api-key-here

# ── Leave empty to use local disk Qdrant (zero setup) ──
QDRANT_URL=
QDRANT_API_KEY=

# ── CORS: allow local frontend ──
ALLOWED_ORIGINS=http://localhost:3000
EOF
fi

echo ""
echo "════════════════════════════════════════════════"
echo "  ✅ Setup complete! To start:"
echo ""
echo "  Backend:  cd backend && uvicorn main:app --reload"
echo "  Frontend: cd frontend && npm run dev"
echo "════════════════════════════════════════════════"
