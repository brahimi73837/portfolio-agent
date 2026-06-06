# 07 — Deploy to Cloud Run

We deploy **two** services: `api` (FastAPI) and `web` (Next.js). Both use `gcloud run deploy --source`,
which builds the Dockerfile with Cloud Build and pushes to Artifact Registry automatically — no manual
image management.

## Prerequisites (done once)

- APIs enabled: `run`, `artifactregistry`, `cloudbuild`, `aiplatform`, `compute`, `secretmanager`.
- Service account `chatbot-api-sa` with `roles/aiplatform.user` and `roles/secretmanager.secretAccessor`.
- Redis VM + `REDIS_URL` secret (chapter 06).
- The FAISS index built locally (`python scripts/ingest.py`) — it's baked into the `api` image, so the
  bot's knowledge ships with the container.

## Deploy the API

```bash
PROJECT=portfolio-agent-499115
REGION=us-central1

gcloud run deploy api \
  --source backend \
  --project $PROJECT --region $REGION \
  --service-account "chatbot-api-sa@${PROJECT}.iam.gserviceaccount.com" \
  --network=default --subnet=default --vpc-egress=private-ranges-only \
  --set-secrets "REDIS_URL=REDIS_URL:latest" \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT},GCP_LOCATION=${REGION},GEMINI_MODEL=gemini-2.5-flash,EMBEDDING_MODEL=text-embedding-005" \
  --memory 1Gi --cpu 1 --min-instances 0 --max-instances 2 --concurrency 20 --timeout 60 \
  --allow-unauthenticated
```

Flag-by-flag:

- `--service-account` → the container authenticates to Vertex AI as this SA (no key files).
- `--network/--subnet/--vpc-egress=private-ranges-only` → **Direct VPC egress** so the container can reach
  the Redis VM's private IP (chapter 06). Public traffic still goes straight out.
- `--set-secrets REDIS_URL=...` → injects the Redis connection string from Secret Manager as an env var.
- `--min-instances 0` → **scales to zero**; you pay nothing when no one's chatting.
- `--max-instances 2 --concurrency 20` → caps fan-out (keeps cost + rate-limit counters concentrated).
- `--allow-unauthenticated` → public endpoint (it's self-protected by guards + limits).

Grab the URL it prints, e.g. `https://api-xxxx-uc.a.run.app`, and smoke-test:

```bash
curl https://api-xxxx-uc.a.run.app/health
# expect: {"status":"ok","kb_ready":true,"redis_ok":true,...}
```

`redis_ok:true` confirms Direct VPC egress → firewall → Redis all work.

## Deploy the Web frontend

Point it at the `api` URL from the previous step:

```bash
API_URL=$(gcloud run services describe api --region $REGION --format='value(status.url)')

gcloud run deploy web \
  --source frontend \
  --project $PROJECT --region $REGION \
  --set-env-vars "BACKEND_URL=${API_URL}" \
  --memory 512Mi --cpu 1 --min-instances 0 --max-instances 2 --concurrency 80 --timeout 60 \
  --allow-unauthenticated
```

The URL it prints (e.g. `https://web-xxxx-uc.a.run.app`) is **the link you share with recruiters**.

## Updating later

- Changed code or your bio? Re-run `python scripts/ingest.py` (if bio changed), then re-run the relevant
  `gcloud run deploy`. Cloud Run rolls out a new revision with zero downtime.
- Changed a knob (rate limits, model)? Update `--set-env-vars` and redeploy `api`.

## Cost recap

- Cloud Run: scale-to-zero; generous free tier; idle = $0.
- e2-micro VM: free tier (one per month in eligible regions).
- Gemini + embeddings: billed to credits; protected by caching + the daily cap.
- Build/registry/secrets: pennies, covered by credits.

Next: [08 — Testing & launch checklist](08-testing-and-launch-checklist.md).
