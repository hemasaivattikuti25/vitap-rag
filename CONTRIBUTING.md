# 🤝 Contributing to vitap-UniOs

First off, thank you for considering contributing to **vitap-UniOs**! It's people like you who make this campus platform awesome for all VIT-AP students.

---

## 🛠️ Code of Conduct
We want to keep this community welcoming, clean, and helpful. Always communicate respectfully and help others.

---

## 🚀 How to Contribute

### 1. Report Bugs or Suggest Features
- Check the [Issues Tab](https://github.com/hemasaivattikuti25/vitap-rag/issues) to make sure it hasn't been reported yet.
- Create a new issue describing the bug, how to reproduce it, or your feature idea.

### 2. Submit Pull Requests (PRs)
- **Fork** the repository and create your branch from `main`.
- Install dependencies for both **backend** and **frontend**.
- Make your changes. Ensure code style is consistent:
  - Backend: Follow PEP 8 style (use `ruff` or `black` for formatting).
  - Frontend: Follow standard Next.js and TypeScript formatting.
- **Run the RAG Evaluation Suite** before pushing:
  ```bash
  cd backend
  python evaluate_rag.py
  ```
  Ensure all tests pass (100% accuracy score).
- Push to your fork and submit a pull request!

---

## 💻 Tech Stack Overview

- **Frontend:** Next.js (App Router), CSS Modules.
- **Backend:** FastAPI (Python), Uvicorn.
- **Vector DB:** Qdrant Cloud / Local disk storage.
- **Inference:** Groq API (LLaMA-3 models).

---

Thank you for contributing! ❤️
