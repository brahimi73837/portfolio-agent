# Implementation Plan: AI Portfolio Chatbot

**Branch**: `001-ai-portfolio-chatbot` | **Date**: 2026-06-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-ai-portfolio-chatbot/spec.md`

## Summary

Build a recruiter-facing chatbot that answers questions about Brahim using RAG over his resume/projects.
A Next.js single-page UI talks to a FastAPI backend that orchestrates retrieval + generation with LangChain,
calling Gemini 2.5 Flash. A FAISS vector store (built from a PDF/text knowledge base with Gemini embeddings)
provides grounding. A single free-tier Redis VM provides response/semantic caching, per-IP rate limiting,
and a global daily budget circuit-breaker. Guardrails keep the bot on-topic, injection-resistant, and unable
to leak. Everything deploys to Google Cloud (Cloud Run + Artifact Registry + Secret Manager) at ≈ $0.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript / Node 20 (frontend).

**Primary Dependencies**:
- Backend: FastAPI, Uvicorn, LangChain + `langchain-google-genai`, `langchain-community` (FAISS, Redis cache),
  `faiss-cpu`, `redis`, `pypdf`, `pydantic-settings`, `slowapi`/custom Redis limiter.
- Frontend: Next.js (App Router), React, Tailwind CSS (minimalist), `react-markdown`.

**Storage**:
- Vector store: FAISS index persisted to disk (`backend/data/faiss_index/`), rebuilt by an ingest script.
- Cache + counters: Redis on an `e2-micro` VM.
- No relational DB. Chat history is client-held and sent per request (last N turns); not persisted server-side.

**Testing**: pytest (backend, LLM mocked) + a small flagged integration suite (real LLM); Playwright/manual
smoke for the UI; a pre-deploy smoke + abuse checklist.

**Target Platform**: Linux containers on Google Cloud Run (two services: `web`, `api`).

**Project Type**: Web application (frontend + backend).

**Performance Goals**: Warm answer < 5s end-to-end (SC-001); cache hit << 1s. Cold start tolerated with UI
typing indicator.

**Constraints**: ≈ $0 steady-state (free tiers + credits); single always-on machine (Redis VM); hard daily
request cap; per-IP rate limit; input/output token caps.

**Scale/Scope**: Low traffic (tens–low-hundreds of sessions). One knowledge base (~a few thousand tokens).
~1 chat screen, ~6 backend modules.

## Constitution Check

*GATE: must pass before and after design.*

| Principle | How this plan complies |
|-----------|------------------------|
| I. Zero marginal cost | Cloud Run scale-to-zero; one `e2-micro` free VM; Gemini free tier; daily circuit-breaker; response caching to avoid repeat calls. |
| II. Defend wallet & brand | Redis per-IP rate limit + global daily cap; input length cap + injection screen; scope/sensitive guardrails; no system-prompt disclosure. |
| III. Spec-driven | This plan derives from approved spec; tasks.md generated next; code follows. |
| IV. Inspectable & teachable | `docs/00..` tutorial series + `MANUAL_SETUP.md`; small, clearly-named modules. |
| V. Right-sized testing | Unit tests mock the LLM; few flagged real-LLM integration tests; one smoke test. |
| VI. LangChain & caching first-class | LCEL chain (retriever → prompt → Gemini → parser); LangChain Redis cache; Gemini context caching for KB. |

**Result**: PASS. No violations → Complexity Tracking left empty.

## Architecture

### Components & data flow

```text
Recruiter browser
      │  HTTPS
      ▼
┌─────────────────────┐        ┌──────────────────────────────────────────────┐
│  web (Next.js)      │  JSON  │  api (FastAPI + LangChain)                    │
│  Cloud Run          │ ─────► │  Cloud Run                                    │
│  - chat UI          │        │                                              │
│  - suggested Qs     │ ◄───── │  request pipeline:                            │
│  - typing indicator │ stream │   1. rate-limit check ........ Redis          │
└─────────────────────┘        │   2. daily budget check ...... Redis          │
                               │   3. input guard (len, injection, scope)      │
                               │   4. cache lookup ............ Redis (LangChain│
                               │        exact + semantic cache)                │
                               │   5. retrieve top-k chunks ... FAISS (RAG)    │
                               │   6. generate ................ Gemini 2.5 Flash│
                               │        (KB context-cached)                    │
                               │   7. store answer in cache ... Redis          │
                               └──────────────────────────────────────────────┘
                                          │                    │
                                          ▼                    ▼
                                 ┌────────────────┐   ┌──────────────────┐
                                 │ FAISS index    │   │ Redis (e2-micro) │
                                 │ (on disk, in   │   │ cache + counters │
                                 │  api container)│   └──────────────────┘
                                 └────────────────┘
                               Gemini API (free tier) ◄── generation + embeddings
```

### Request pipeline (order matters — cheapest/safest checks first)

1. **Rate limit** (per-IP sliding window in Redis) → 429-style friendly message, no LLM call.
2. **Global daily budget** (Redis counter w/ midnight TTL) → if exceeded, circuit-break to canned/cached reply.
3. **Input guard**: trim; reject empty; truncate to input cap; run injection/jailbreak heuristics; run a cheap
   scope check. Off-topic/sensitive → canned refusal, no LLM call.
4. **Cache lookup**: LangChain Redis cache (exact key) then semantic cache (embedding similarity ≥ threshold).
   Hit → return cached answer (log hit), no generation call.
5. **Retrieve**: embed the (history-condensed) question, FAISS similarity search → top-k chunks.
6. **Generate**: LCEL chain feeds system prompt + retrieved context + last N turns to Gemini 2.5 Flash with
   max-output-token cap. KB/system context served via Gemini context caching to cut input-token cost.
7. **Persist** answer in Redis cache (namespaced by KB version) and return; stream tokens to UI.

### Caching strategy (three layers — explicit, since it's a graded goal)

- **L1 Exact response cache** (`RedisCache`): identical normalized question → identical answer. TTL'd,
  namespaced by `kb_version` so a re-ingest invalidates stale answers (FR-018).
- **L2 Semantic cache** (`RedisSemanticCache`): near-duplicate questions (cosine ≥ threshold) reuse an answer
  without a generation call (FR-013).
- **L3 Context cache** (Gemini context caching): the system prompt + retrieved KB context is cached on the
  model side so repeated turns don't re-bill full input tokens (FR-014). Falls back to plain calls if
  unavailable.

### Guardrails design

- **Input cap**: hard max chars; over-limit rejected, soft-limit truncated.
- **Injection/jailbreak heuristics**: deny-list patterns ("ignore previous", "system prompt", "developer mode",
  role-override, exfiltration asks) → treated as off-topic; never echoed back into the prompt unescaped.
- **Scope + sensitivity**: strong system prompt instructing the model to answer only about Brahim's
  professional profile, to refuse sensitive/personal data, and to use the canned line for off-topic. Backed by
  a lightweight pre-classifier (keyword + optional tiny model call) so obvious off-topic never reaches generation.
- **Output**: system prompt forbids revealing instructions/infra; max output tokens capped.

### Failure modes (graceful degradation)

- Redis down → disable caching, fall back to a conservative in-process rate limit (fail closed on cost).
- Gemini error/timeout → friendly retry message, logged.
- KB not ingested → `/health` reports not-ready; chat returns clear "not ready" state.

## Project Structure

### Documentation (this feature)

```text
specs/001-ai-portfolio-chatbot/
├── spec.md          # approved specification
├── plan.md          # this file
└── tasks.md         # generated next (/speckit-tasks)

docs/                                 # tutorial-grade build guide (repo root)
├── 00-overview.md
├── 01-local-setup.md
├── 02-knowledge-base-and-ingest.md
├── 03-backend-langchain-rag.md
├── 04-caching-and-guardrails.md
├── 05-frontend-nextjs.md
├── 06-redis-vm.md
├── 07-deploy-cloud-run.md
└── 08-testing-and-launch-checklist.md

MANUAL_SETUP.md                       # everything the human must do by hand
```

### Source code (repository root)

```text
backend/
├── app/
│   ├── main.py             # FastAPI app, routes: POST /chat, GET /health
│   ├── config.py           # pydantic-settings, env-driven
│   ├── chain.py            # LangChain LCEL: retriever → prompt → Gemini → parser
│   ├── retriever.py        # FAISS load + similarity search
│   ├── cache.py            # Redis exact + semantic cache wiring
│   ├── guardrails.py       # input cap, injection screen, scope/sensitivity
│   ├── ratelimit.py        # per-IP limit + global daily budget (Redis)
│   └── prompts.py          # system prompt + refusal templates
├── scripts/
│   └── ingest.py           # PDF/text → chunks → embeddings → FAISS (+ bump kb_version)
├── data/
│   ├── knowledge/          # source PDF/text about Brahim (gitignored if private)
│   └── faiss_index/        # built index (gitignored)
├── tests/
│   ├── unit/               # retriever, cache, guardrails, ratelimit (LLM mocked)
│   └── integration/        # few real-LLM checks, flagged
├── Dockerfile
├── requirements.txt
└── .env.example

frontend/
├── app/
│   ├── page.tsx            # single chat screen
│   ├── layout.tsx
│   └── api/chat/route.ts   # thin proxy to backend (keeps backend URL/secret server-side)
├── components/
│   ├── ChatWindow.tsx
│   ├── MessageBubble.tsx
│   └── SuggestedQuestions.tsx
├── lib/api.ts
├── Dockerfile
├── package.json
└── .env.example

deploy/
├── redis/cloud-init.yaml   # e2-micro Redis bootstrap
└── cloudrun/*.md           # gcloud commands (also in docs/07)

.gitignore
README.md
```

**Structure Decision**: Web application — separate `backend/` (Python/LangChain) and `frontend/` (Next.js),
each its own Cloud Run service, matching the requested stack and giving a clean, demonstrable architecture.

## Build phases (maps to docs/ and tasks.md)

- **Phase A — Local core**: ingest script + FAISS; LangChain RAG chain; FastAPI `/chat` + `/health`; run locally.
- **Phase B — Caching & guardrails**: Redis caches, rate limit, daily cap, injection/scope guards; unit tests.
- **Phase C — Frontend**: Next.js chat UI + proxy route; wire to backend; local end-to-end.
- **Phase D — Infra**: e2-micro Redis VM; Secret Manager; Artifact Registry.
- **Phase E — Deploy**: containerize + deploy both services to Cloud Run; smoke test; abuse checklist; share URL.

Each phase ends with its `docs/` chapter and a commit.

## Complexity Tracking

No constitution violations. (Two Cloud Run services instead of one is justified by the requested
frontend/backend split and the Python-only LangChain ecosystem; both scale to zero, preserving Principle I.)
