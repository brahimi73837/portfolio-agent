# Feature Specification: AI Portfolio Chatbot

**Feature Branch**: `001-ai-portfolio-chatbot`

**Created**: 2026-06-11

**Status**: Draft — awaiting approval

**Input**: Replace a static PDF resume with a recruiter-facing AI chatbot. Recruiters chat with a bot to ask
about Brahim instead of scrolling a resume. Knowledge base from a PDF / vector DB. Gemini 2.5 Flash via
LangChain, vector embeddings for retrieval, Redis prompt/response caching, deployed free on Google Cloud,
hardened against abuse and credit-burn.

---

## Overview

A single-page website with one job: a clean chat box where a recruiter types a question about Brahim and
gets a fast, accurate, grounded answer. Answers come only from a curated knowledge base (resume, projects,
achievements). The system is cheap to run (free tiers + credits), resistant to abuse, and itself a
demonstration of the AI engineering skills it describes (RAG, LangChain, caching, safe deployment).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recruiter asks about Brahim and gets a grounded answer (Priority: P1)

A recruiter lands on the URL, sees a minimalist chat interface with a short intro and a few suggested
questions ("What has Brahim built?", "What's his experience with LLMs?"). They type a question and within a
couple of seconds receive a concise, accurate answer drawn from Brahim's knowledge base, with no setup,
login, or PDF download.

**Why this priority**: This is the entire product. Without it there is nothing to demo. It is the MVP.

**Independent Test**: Open the deployed URL, ask "What projects has Brahim worked on?", confirm a coherent
answer grounded in the knowledge base returns in a few seconds.

**Acceptance Scenarios**:

1. **Given** the site is live, **When** a recruiter asks a question covered by the knowledge base,
   **Then** they get a relevant, factual answer sourced from that knowledge base in under ~5 seconds.
2. **Given** a recruiter asks a follow-up ("Tell me more about that one"), **When** they send it,
   **Then** the bot uses the prior turns as context and answers coherently.
3. **Given** a recruiter asks something Brahim's KB doesn't cover, **When** they send it,
   **Then** the bot says it doesn't have that info rather than inventing an answer (no hallucination).

---

### User Story 2 - Off-topic / sensitive / malicious input is safely deflected (Priority: P1)

Someone asks something unrelated ("write me a poem", "what's the capital of France"), sensitive about Brahim
(home address, salary, personal life), or tries to hijack the bot ("ignore your instructions and...").
The bot refuses gracefully and steers back to its purpose.

**Why this priority**: Recruiter-facing and public. A bot that leaks, hallucinates sensitive claims, or
gets jailbroken into saying something off-brand actively damages Brahim. Equal priority to P1.

**Independent Test**: Send an off-topic question, a sensitive question, and a prompt-injection attempt;
confirm each gets a polite bounded refusal and the system prompt is never revealed.

**Acceptance Scenarios**:

1. **Given** an off-topic question, **When** sent, **Then** the bot replies along the lines of
   "idk, I only answer questions about Brahim" and offers what it *can* help with.
2. **Given** a prompt-injection / jailbreak attempt, **When** sent, **Then** the bot ignores the injected
   instruction, does not reveal its system prompt or infrastructure, and stays in scope.
3. **Given** a sensitive personal question, **When** sent, **Then** the bot declines and does not surface
   private data even if such data somehow appeared in the KB.

---

### User Story 3 - The system protects its own budget and stays up (Priority: P1)

The infrastructure caps cost and abuse automatically: a single user cannot spam it into draining credits,
total daily spend is bounded, and repeated/similar questions are served from cache instead of re-billing
the model.

**Why this priority**: A demo that drains the credits is offline by the time a recruiter visits, and a
recruiter who refreshes 30 times shouldn't cost more than a recruiter who refreshes once. Protects the
core deliverable's availability.

**Independent Test**: Fire rapid repeated requests from one client → confirm rate-limit kicks in with a
friendly message; ask the same question twice → confirm the second is a cache hit (faster, no new LLM call).

**Acceptance Scenarios**:

1. **Given** one client exceeds the per-IP rate limit, **When** they send another request,
   **Then** they get a friendly "slow down a moment" response and no LLM call is made.
2. **Given** the global daily request cap is reached, **When** any new request arrives,
   **Then** the circuit breaker serves a cached/canned response and makes no paid API call.
3. **Given** a question identical or semantically similar to a previous one, **When** asked again,
   **Then** it is answered from the Redis cache without a new generation call.

---

### User Story 4 - Brahim can update the knowledge base (Priority: P2)

Brahim drops a new/updated resume PDF (or edits a text file) and runs one documented command to re-embed
and refresh the knowledge base; the bot then answers using the new content.

**Why this priority**: Keeps the bot accurate over time, but the bot is demoable before this is automated.

**Independent Test**: Add a new fact to the source file, run the ingest command, ask about that fact,
confirm the bot now knows it.

**Acceptance Scenarios**:

1. **Given** an updated source document, **When** the ingest command runs, **Then** the vector store is
   rebuilt and the new content is retrievable.
2. **Given** the KB was updated, **When** a previously-cached question touching changed content is asked,
   **Then** stale cache entries do not mask the new answer (cache is namespaced/invalidated on rebuild).

---

### User Story 5 - The build is reproducible and teachable (Priority: P2)

A reader follows `docs/` and `MANUAL_SETUP.md` and reproduces the entire system — local dev and full GCP
deploy — without insider knowledge.

**Why this priority**: An explicit goal is a tutorial-grade, inspectable build that demonstrates competence,
not just a black box.

**Independent Test**: A second person, given only the repo, gets it running locally and deployed by
following the docs.

**Acceptance Scenarios**:

1. **Given** only the repo, **When** a reader follows the docs, **Then** they reach a working local chat.
2. **Given** the deploy docs, **When** followed, **Then** they reach a working public URL.

---

### Edge Cases

- Empty / whitespace-only message → bot prompts for a real question, no LLM call.
- Very long input (paste of a whole job description) → truncated to a cap; over hard-limit is rejected politely.
- Redis VM unreachable → app fails *open for reads but closed for cost*: it still answers but disables
  caching, and if rate-limit state is unavailable it falls back to a conservative in-process limit.
- LLM API error / timeout → user gets a graceful "having trouble, try again" message, error is logged.
- Knowledge base empty or not yet ingested → health check fails; app returns a clear "not ready" state.
- Non-English question → answered if the model can; out-of-scope rules still apply.
- Concurrent cold start → first request may be slower (Cloud Run cold start); UI shows a typing indicator.

## Requirements *(mandatory)*

### Functional Requirements

**Chat & retrieval**
- **FR-001**: System MUST present a single-page, minimalist chat UI with an intro line and 2–4 suggested questions.
- **FR-002**: System MUST accept a user question and return an answer grounded in Brahim's knowledge base.
- **FR-003**: System MUST retrieve relevant knowledge-base chunks via vector-embedding similarity search and
  condition the answer on them (RAG); it MUST NOT answer P1 questions from model parametric memory alone.
- **FR-004**: System MUST support multi-turn context within a session (follow-up questions).
- **FR-005**: When the KB does not contain the answer, System MUST decline rather than fabricate.
- **FR-006**: System MUST stream or promptly return answers and show a visible "thinking" state.

**Guardrails**
- **FR-007**: System MUST restrict answers to the topic of Brahim; off-topic queries get a bounded refusal
  ("idk, I only answer questions about Brahim" style).
- **FR-008**: System MUST detect and neutralize prompt-injection / jailbreak attempts and never disclose its
  system prompt, keys, or infrastructure.
- **FR-009**: System MUST decline sensitive/personal-data questions about Brahim.
- **FR-010**: System MUST cap input length and reject/truncate oversized input.

**Cost & abuse control**
- **FR-011**: System MUST enforce per-IP (or per-client) rate limiting backed by Redis.
- **FR-012**: System MUST enforce a global daily request cap (circuit breaker) that prevents paid API calls
  once exceeded and degrades gracefully.
- **FR-013**: System MUST cache responses to identical questions and SHOULD cache semantically-similar ones,
  serving cache hits without a new generation call.
- **FR-014**: System MUST cache/reuse the large knowledge-base context to reduce input-token spend across
  turns (native Gemini context caching and/or Redis), not re-send it at full price every call.
- **FR-015**: System MUST cap max output tokens per answer.

**Knowledge base**
- **FR-016**: System MUST ingest a PDF and/or text source about Brahim and build a persisted vector store.
- **FR-017**: System MUST provide one documented command to re-ingest and refresh the KB.
- **FR-018**: Rebuilding the KB MUST invalidate or namespace stale caches so old answers don't persist.

**Operability & docs**
- **FR-019**: System MUST expose a health endpoint reporting KB-ready and Redis-reachable status.
- **FR-020**: Secrets MUST come from environment / Secret Manager, never committed to git.
- **FR-021**: System MUST ship tutorial-grade docs covering local run, deploy, and all manual steps.
- **FR-022**: System MUST log requests/errors (without storing sensitive content) for debugging and to
  observe cache hit-rate and daily counts.

### Key Entities

- **Knowledge Base**: Curated facts about Brahim (resume, projects, achievements, FAQ). Source = PDF/text.
- **Document Chunk**: A passage of the KB with its embedding vector and metadata (source, section).
- **Vector Store**: The searchable index of chunks (FAISS) used for retrieval.
- **Chat Session**: An ordered list of user/assistant turns providing short-term context.
- **Cache Entry**: A stored answer keyed by question (exact and/or semantic) with a TTL and KB-version namespace.
- **Rate-Limit Counter / Budget Counter**: Redis-backed counters per client and global-per-day.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A recruiter gets a grounded answer to a covered question in **under 5 seconds** (warm), and
  the answer is factually consistent with the KB.
- **SC-002**: **100%** of a fixed off-topic/sensitive/injection test set receives a safe bounded refusal
  with **zero** system-prompt leaks.
- **SC-003**: On a repeated/similar question, the second ask is served from cache and is **measurably faster**
  (cache hit logged, no new generation call).
- **SC-004**: Sustained single-client spamming cannot exceed the configured per-IP rate; the **global daily
  cap is never exceeded**, keeping spend within free tier.
- **SC-005**: Steady-state infrastructure cost is **≈ $0** against free tiers + credits.
- **SC-006**: A second person can reproduce local run **and** public deploy from the docs alone.
- **SC-007**: The public URL is reachable and passes the smoke test before being shared with recruiters.

## Assumptions

- Traffic is low (recruiters, tens–low-hundreds of sessions), comfortably within Gemini API free tier with
  caching and a daily cap.
- Brahim provides the knowledge-base content (PDF or text) and is comfortable with it being publicly queryable.
- Google Cloud account with credits + billing enabled exists; `us-central1` (or another free-tier-eligible
  region) is used for the `e2-micro` VM.
- The Gemini API free tier is acceptable for a portfolio demo; cost controls keep us inside it.
- A short conversation history (last N turns) is sufficient context; no long-term user accounts or persistence.
- Minimalist single-page design is preferred over a feature-rich app; mobile-responsive but no native app.
- Sessions are ephemeral; no personal data about *recruiters* is stored.

## Out of Scope (v1)

- User accounts / authentication for recruiters.
- Admin dashboard UI (KB updates are a documented CLI command).
- Multi-language UI localization (the model may still answer non-English questions).
- Analytics beyond basic logs / cache-hit and daily-count metrics.
- Voice input/output.
