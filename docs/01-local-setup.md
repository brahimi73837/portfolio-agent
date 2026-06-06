# 01 — Local setup

Goal: run the whole thing on your laptop in ~10 minutes.

## Prerequisites

- **Python 3.12** and **Node 20** (we use [`uv`](https://docs.astral.sh/uv/) to get Python 3.12 quickly).
- **gcloud CLI**, authenticated, with the project set (see [MANUAL_SETUP.md](../MANUAL_SETUP.md) steps 1–4).
- **Docker** (only needed if you want a local Redis; optional — the app degrades gracefully without it).

Authenticate for local Vertex AI calls (uses your user credentials, billed to credits):

```bash
gcloud auth application-default login
gcloud config set project portfolio-agent-499115
```

## Backend

```bash
cd backend
uv venv --python 3.12 .venv          # create an isolated Python 3.12 env
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env                  # defaults are fine for local dev
```

Build the knowledge index (see [02](02-knowledge-base-and-ingest.md)) then run the API:

```bash
.venv/bin/python scripts/ingest.py    # builds data/faiss_index/
.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

Check it:

```bash
curl localhost:8000/health
# {"status":"ok","kb_ready":true,"redis_ok":false,"kb_version":"...","model":"gemini-2.5-flash"}
```

`redis_ok:false` is fine locally — caching just turns off. To enable it, run Redis in Docker:

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

## Frontend

```bash
cd ../frontend
npm install
echo "BACKEND_URL=http://localhost:8000" > .env
npm run dev          # http://localhost:3000
```

Open http://localhost:3000 and ask a question. 🎉

## Project layout

```
backend/   FastAPI + LangChain (the brain)
frontend/  Next.js chat UI (the face)
docs/      this tutorial
specs/     the Spec Kit specification & plan
deploy/    infra helpers (Redis VM, Cloud Run notes)
```

Next: [02 — Knowledge base & ingest](02-knowledge-base-and-ingest.md).
