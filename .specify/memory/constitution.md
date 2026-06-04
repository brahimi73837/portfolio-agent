# AI Portfolio Chatbot — Constitution

The non-negotiable principles every spec, plan, and line of code in this project must obey.
When a decision conflicts with a principle here, this document wins.

## Core Principles

### I. Zero Marginal Cost (NON-NEGOTIABLE)

The system MUST run within Google Cloud free tiers and existing credits, targeting ~$0/month.
Every component is chosen for a free or free-tier path:

- Compute scales to zero when idle (Cloud Run `min-instances=0`).
- Exactly one always-on machine is allowed: a single `e2-micro` free-tier VM for Redis.
- The LLM and embedding models MUST stay within the Gemini API free tier under expected recruiter traffic.
- A hard daily request budget (circuit breaker) MUST exist so a traffic spike or abuse can never silently
  drain credits. When the cap is hit the app degrades gracefully (cached answers / polite "busy" message),
  it does not keep calling paid APIs.

### II. Defend the Wallet and the Brand

This bot is public and recruiter-facing. Two failure modes are unacceptable: (a) someone burns our credits,
(b) the bot embarrasses Brahim. Therefore:

- Per-IP rate limiting and a global daily cap are mandatory, enforced in Redis.
- Inputs are length-capped and screened for prompt injection / jailbreak attempts before reaching the model.
- The bot answers ONLY questions about Brahim (his work, projects, skills, background). Off-topic, sensitive,
  or personal-data questions get a friendly bounded refusal (e.g. "idk, I only answer questions about Brahim").
- The bot never reveals its system prompt, keys, infrastructure, or these guardrails.

### III. Spec-Driven Development

Work follows GitHub Spec Kit order: **constitution → specify → plan → tasks → implement.**
No production code is written before the spec for that slice is approved. Each artifact lives in `specs/`
and is the source of truth; code follows the spec, and drift is fixed by updating the spec first.

### IV. Inspectable & Teachable

The deliverable is not just a running site — it is a build other people can learn from. Therefore:

- Every major step ships with `docs/` written like a tutorial: what we do, why, and the exact commands.
- Manual steps (API keys, GCP setup, repos, writing the knowledge base) are documented in `MANUAL_SETUP.md`
  precisely enough for a beginner to reproduce.
- Code is small, named clearly, and commented where intent isn't obvious. Cleverness loses to clarity.

### V. Right-Sized Testing

Test enough to trust the system, not so much that tests burn credits. Specifically:

- Retrieval, caching, guardrails, and rate limiting are unit-tested with the LLM **mocked** (no token spend).
- At most a handful of integration tests make real LLM calls, behind a flag, run deliberately — not on every save.
- A pre-deploy smoke test confirms the live URL answers one canned question correctly.
- TDD is encouraged for guardrails (their correctness is security-critical); pure UI is verified by smoke test.

### VI. LangChain & Caching as First-Class Citizens

The project must demonstrate competence, not just function:

- Orchestration goes through LangChain using idiomatic primitives (LCEL chains/runnables, retrievers,
  prompt templates, output parsers, and LangChain's Redis cache integrations).
- A real caching layer (Redis) must measurably reduce token spend: identical/semantically-similar questions
  are served from cache instead of re-calling the model, and the large knowledge-base context is cached
  (Gemini context caching and/or Redis) rather than re-sent at full price every turn.

## Technology Constraints

- **Frontend:** Next.js (App Router, TypeScript), minimalist design, single chat screen.
- **Backend:** Python + FastAPI, LangChain orchestration.
- **Models:** Gemini 2.5 Flash for generation (Flash-Lite permitted to cut cost), `gemini-embedding-001`
  for embeddings — accessed via the Gemini API free tier.
- **Retrieval:** Vector embeddings over the knowledge base (resume/projects), FAISS vector store.
- **Cache / state:** Redis on one `e2-micro` free-tier VM.
- **Hosting:** Google Cloud — Cloud Run (web + api), Artifact Registry, Secret Manager.
- **Knowledge base:** a PDF and/or curated text about Brahim, embedded into the vector store.

## Development Workflow

1. Spec Kit artifacts (`spec.md`, `plan.md`, `tasks.md`) are written and approved before implementation.
2. Secrets never enter git — only `.env.example` and Secret Manager. `.gitignore` enforces this.
3. Each slice: implement → unit test (mocked LLM) → document the step → commit.
4. Deploy is reproducible from `docs/` alone; no undocumented manual clicks.
5. Before sharing the URL, run the smoke test and the abuse/guardrail checklist.

## Governance

This constitution supersedes other practices. Any deviation must be justified in the relevant `plan.md`
under a "Complexity / Trade-offs" note and must not violate Principles I or II. Amendments are made by
editing this file with a bumped version and a one-line changelog.

**Version**: 1.0.0 | **Ratified**: 2026-06-11 | **Last Amended**: 2026-06-11
