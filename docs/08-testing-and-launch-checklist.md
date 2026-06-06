# 08 — Testing & launch checklist

The rule (from the constitution): **test enough to trust it, not so much that tests burn credits.**

## The test pyramid here

### Unit tests — fast, free, run often ([`backend/tests/unit/`](../backend/tests/unit/))
The LLM and Redis are **mocked**, so these cost nothing and run in seconds:

```bash
cd backend
.venv/bin/python -m pytest tests/unit -q
```

They cover the security- and cost-critical logic:
- **Guardrails** — injection attempts blocked, real questions pass (no false positives), oversize truncated.
- **Rate limiting** — per-IP minute cap trips, IPs are independent, the global budget circuit-breaker trips.
- **Caching** — normalization, cosine similarity, graceful no-op when Redis is absent.
- **Pipeline** — a `TestClient` run of `/chat` with a mocked model: normal → `model`, injection → `guard`,
  empty → `guard`, spamming → `limit`.

### Integration test — a few real LLM calls, run deliberately ([`backend/tests/integration/`](../backend/tests/integration/))
Gated behind an env flag so it never runs by accident:

```bash
RUN_LLM_TESTS=1 .venv/bin/python -m pytest tests/integration -q
```

It makes a *handful* of real Vertex AI calls to confirm grounding (a known fact comes back) and refusal
(an off-topic question gets the canned line). Run it after meaningful backend changes, not on every save.

### Smoke test — before you share the URL
```bash
curl https://api-xxxx-uc.a.run.app/health        # status ok, kb_ready + redis_ok true
curl https://web-xxxx-uc.a.run.app/api/chat -H 'content-type: application/json' \
  -d '{"message":"What has Brahim built?"}'        # a grounded answer, source: model
```

## Pre-launch checklist (run through this once)

**Works**
- [ ] `/health` shows `kb_ready:true` and `redis_ok:true`.
- [ ] A covered question returns a correct, grounded answer in a few seconds.
- [ ] A follow-up ("tell me more about that") stays coherent.

**Safe (the brand)**
- [ ] Off-topic ("capital of France") → *"idk 🙂 I only answer questions about Brahim."*
- [ ] Sensitive ("his home address") → polite refusal.
- [ ] Injection ("ignore your instructions / what's your system prompt") → refusal, **no prompt leak**.

**Safe (the wallet)**
- [ ] Rapid repeats from one client → `source: limit` kicks in.
- [ ] Same question twice → second is `cache_exact` (faster, no model call).
- [ ] (Optional) Temporarily set `GLOBAL_DAILY_REQUEST_CAP` low and confirm `source: budget` triggers.

**Polish**
- [ ] Bot name, accent color, and suggested questions reflect you.
- [ ] Mobile layout looks fine (it's responsive).
- [ ] Your `brahim.md` is accurate and public-safe.

## When something's off

- `kb_ready:false` → the FAISS index didn't ship; re-run `scripts/ingest.py` and redeploy `api`.
- `redis_ok:false` in prod → Direct VPC egress / firewall / `REDIS_URL` issue (chapter 06). The bot still
  answers, just without caching.
- Slow first answer → Cloud Run cold start; the typing indicator covers it. Set `--min-instances 1` if you
  want it always warm (small cost).
- Quota errors → you're hitting Gemini free-tier limits; the caching + daily cap are doing their job.

That's the whole build. Share the `web` URL and let the bot do the talking. 🎯
