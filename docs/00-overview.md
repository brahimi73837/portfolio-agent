# 00 — Overview: what we're building and why

> This `docs/` series is a build-along tutorial. Read it top to bottom and you can recreate the whole
> system. Each chapter is one phase, with the *why* before the *how*.

## The idea

A static PDF resume is a dead end — a recruiter skims it and moves on. We replace it with a **chatbot**:
the recruiter asks questions ("What has Brahim built?", "Does he know LangChain?") and gets instant,
accurate answers. It's more engaging *and* it demonstrates the exact skills the resume claims.

## The hard parts (and how we solve them)

| Challenge | Our solution |
|---|---|
| Answers must be true, not hallucinated | **RAG**: retrieve facts from a knowledge base and make the model answer only from them |
| It's public → people will abuse it | **Guardrails** (scope/injection) + **rate limits** + a **daily budget circuit-breaker** |
| LLM calls cost money | **Redis caching** (exact + semantic) so repeat questions don't re-bill the model |
| Must be ~free | Gemini on credits, Cloud Run scale-to-zero, one free-tier VM |
| Must impress | Fast, clean, minimalist single-page chat |

## Architecture in one picture

```
Browser ──► web (Next.js, Cloud Run) ──► api (FastAPI + LangChain, Cloud Run) ──► Gemini 2.5 Flash (Vertex AI)
                                              │                     │
                                         FAISS (RAG)          Redis (e2-micro VM): cache + rate limit + budget
```

Request pipeline inside `api` (cheapest, safest checks first):

```
rate limit ─► input guard ─► exact cache ─► embed once ─► semantic cache ─► budget ─► retrieve + generate ─► cache it
```

## The stack and why each piece

- **Next.js** — fast, minimal single-page chat; easy to deploy; the proxy route hides the backend and
  forwards the real client IP so rate-limiting works.
- **FastAPI + LangChain** — Python is the native home of LangChain; FastAPI is a tiny, fast API layer.
  LangChain gives us idiomatic RAG (retriever → prompt → model → parser) and a Redis LLM cache.
- **Gemini 2.5 Flash on Vertex AI** — strong, cheap, and billed to your Google Cloud credits (no separate
  key to manage; Cloud Run authenticates as a service account).
- **FAISS** — a local vector index; zero infrastructure, perfect for a small knowledge base.
- **Redis on an e2-micro VM** — the free-tier "always-on" box that holds caches and counters.
- **Cloud Run** — serverless containers that **scale to zero**, so you pay nothing between visits.

## How to read the rest

1. [01 — Local setup](01-local-setup.md)
2. [02 — Knowledge base & ingest](02-knowledge-base-and-ingest.md)
3. [03 — Backend: LangChain RAG](03-backend-langchain-rag.md)
4. [04 — Caching & guardrails](04-caching-and-guardrails.md)
5. [05 — Frontend (Next.js)](05-frontend-nextjs.md)
6. [06 — Redis VM](06-redis-vm.md)
7. [07 — Deploy to Cloud Run](07-deploy-cloud-run.md)
8. [08 — Testing & launch checklist](08-testing-and-launch-checklist.md)

Before any of that, the human-only steps (accounts, keys, your bio) live in
[MANUAL_SETUP.md](../MANUAL_SETUP.md).
