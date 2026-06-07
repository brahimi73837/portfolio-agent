# Brahim — AI Portfolio Chatbot

An interactive, recruiter-facing chatbot that replaces a static PDF resume. Ask it about Brahim's work,
projects, and skills and it answers — grounded in a curated knowledge base, fast, and cheap to run.

**🔴 Live:** https://web-328999069793.us-central1.run.app
&nbsp;·&nbsp; API: https://api-5iuake3yoq-uc.a.run.app/health

It is also a demonstration of the skills it describes: **RAG over vector embeddings, LangChain orchestration,
Gemini 2.5 Flash, Redis caching, guardrails, and a ≈ $0 Google Cloud deployment.**

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router, TypeScript), minimalist chat UI |
| Backend | Python + FastAPI + LangChain |
| LLM | Gemini 2.5 Flash (via Gemini API free tier) |
| Embeddings / retrieval | `gemini-embedding-001` + FAISS vector store |
| Cache / rate limit / budget | Redis on one free-tier `e2-micro` VM |
| Hosting | Google Cloud Run (×2) + Artifact Registry + Secret Manager |

## How it's built (spec-driven, GitHub Spec Kit)

- Principles: [.specify/memory/constitution.md](.specify/memory/constitution.md)
- Specification: [specs/001-ai-portfolio-chatbot/spec.md](specs/001-ai-portfolio-chatbot/spec.md)
- Technical plan: [specs/001-ai-portfolio-chatbot/plan.md](specs/001-ai-portfolio-chatbot/plan.md)
- **Human setup checklist: [MANUAL_SETUP.md](MANUAL_SETUP.md)**
- Tutorial build guide: [docs/](docs/) (written like a step-by-step course)

## Quick start

See [MANUAL_SETUP.md](MANUAL_SETUP.md) for accounts/keys, then [docs/01-local-setup.md](docs/01-local-setup.md)
to run locally, and [docs/07-deploy-cloud-run.md](docs/07-deploy-cloud-run.md) to deploy.

> Status: **Deployed & live.** Built end-to-end (backend, frontend, RAG, caching, guardrails, infra) and
> running on Google Cloud. Replace `backend/data/knowledge/brahim.md` with your real bio
> (see [KNOWLEDGE_QUESTIONS.md](KNOWLEDGE_QUESTIONS.md)), re-run `scripts/ingest.py`, and redeploy `api`.
