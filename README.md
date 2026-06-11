# Portfolio Agent

An interactive AI chatbot that answers recruiter questions about me (Brahim Elkhattabi) instead of a static PDF resume. Ask it about my projects, skills, and experience and it replies in seconds, grounded in a curated knowledge base.

**Live:** https://brahimi73837.github.io/portfolio-agent/

It is also a working demo of the things it talks about: retrieval-augmented generation, LangChain orchestration, prompt/response caching, abuse protection, and a near zero-cost Google Cloud deployment.

## Stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js (App Router, TypeScript), Tailwind |
| Backend | Python, FastAPI, LangChain |
| Model | Gemini 2.5 Flash on Vertex AI |
| Retrieval | `text-embedding-005` + FAISS vector store |
| Cache / rate limiting | Redis on a free-tier Compute Engine VM |
| Hosting | Google Cloud Run (web + api), Artifact Registry, Secret Manager |

## How it works

A recruiter's question flows through a small, deliberately cheap-first pipeline in the `api` service:

```
rate limit  ->  input guard  ->  exact cache  ->  embed once
            ->  semantic cache  ->  daily budget  ->  retrieve + generate  ->  cache
```

- **Grounded answers.** The question is embedded, the most relevant chunks of the knowledge base are retrieved from FAISS (using MMR for diversity), and the model answers only from that context. If the answer is not in the knowledge base, it says so instead of guessing.
- **Guardrails.** Off-topic, sensitive, or prompt-injection inputs are deflected. The bot only talks about my professional background and never exposes its instructions.
- **Caching.** Identical and semantically similar questions are served from Redis without a new model call. The knowledge-base version is part of every cache key, so updating it invalidates stale answers automatically.
- **Cost control.** Per-IP rate limits plus a global daily cap stop anyone from draining credits. Cloud Run scales to zero, so idle cost is nothing.
- **Slash commands.** `/projects`, `/skills`, `/contact`, `/github`, and more return instant pre-built answers with no model call.

## Run it locally

Backend:

```bash
cd backend
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env
.venv/bin/python scripts/ingest.py
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Frontend:

```bash
cd frontend
npm install
echo "BACKEND_URL=http://localhost:8000" > .env
npm run dev   # http://localhost:3000
```

Tests:

```bash
cd backend && .venv/bin/python -m pytest tests/unit -q
```

## Knowledge base

The bot answers from `backend/data/knowledge/brahim.md`. Edit that file and re-run `scripts/ingest.py` to rebuild the index, then redeploy the `api` service.

## Project layout

```
backend/    FastAPI + LangChain (retrieval, caching, guardrails, rate limiting)
frontend/   Next.js chat UI and a server proxy that forwards the client IP
specs/      Specification and implementation plan (built spec-first)
pages/      GitHub Pages redirect to the live app
```
