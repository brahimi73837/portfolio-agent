# 09 — Exact command log (everything that was actually run)

This is the literal sequence of commands used to build, provision, and deploy the system, with the real
values for this project. Use it to reproduce or audit the build. Secrets are never shown (they live in
`.env` / Secret Manager).

Project facts:
- **GCP project:** `portfolio-agent-499115` (number `328999069793`)
- **Region / zone:** `us-central1` / `us-central1-a`
- **Service account:** `chatbot-api-sa@portfolio-agent-499115.iam.gserviceaccount.com`

---

## A. Tooling

```bash
# uv (gets us Python 3.12 + fast installs) — standalone, no system Python changes
curl -LsSf https://astral.sh/uv/install.sh | sh        # installs to ~/.local/bin
export PATH="$HOME/.local/bin:$PATH"
```

## B. Spec Kit scaffold

```bash
cd portfolio_agent
git init
uvx --from git+https://github.com/github/spec-kit.git specify init \
  --here --integration claude --ignore-agent-tools --force --script sh
# -> creates .specify/ (templates, scripts, memory/constitution.md) and .claude/skills/speckit-*

# create the feature folder + spec stub
bash .specify/scripts/bash/create-new-feature.sh \
  --short-name "ai-portfolio-chatbot" "Recruiter-facing AI portfolio chatbot ..."
# -> specs/001-ai-portfolio-chatbot/spec.md
```

(We then wrote `constitution.md`, `spec.md`, and `plan.md` by hand.)

## C. Google Cloud setup

```bash
PROJECT=portfolio-agent-499115
REGION=us-central1

# point gcloud + Application Default Credentials at the project
gcloud config set project $PROJECT
gcloud auth application-default set-quota-project $PROJECT

# verify access + billing
gcloud projects describe $PROJECT --format="value(projectId,projectNumber,lifecycleState)"
gcloud beta billing projects describe $PROJECT --format="value(billingEnabled,billingAccountName)"

# enable every API we use
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com --project $PROJECT
```

Quick proof Vertex AI works (model + embeddings) before building around it:

```bash
TOKEN=$(gcloud auth application-default print-access-token)
curl -s -X POST \
  "https://$REGION-aiplatform.googleapis.com/v1/projects/$PROJECT/locations/$REGION/publishers/google/models/gemini-2.5-flash:generateContent" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"contents":[{"role":"user","parts":[{"text":"Reply with: ok"}]}],"generationConfig":{"maxOutputTokens":5}}'
# and text-embedding-005 :predict  -> returns a 768-dim vector
```

## D. Service account for the API

```bash
SA=chatbot-api-sa
gcloud iam service-accounts create $SA --display-name="Portfolio Chatbot API" --project $PROJECT
SA_EMAIL="${SA}@${PROJECT}.iam.gserviceaccount.com"

for ROLE in roles/aiplatform.user roles/secretmanager.secretAccessor; do
  gcloud projects add-iam-policy-binding $PROJECT \
    --member="serviceAccount:${SA_EMAIL}" --role="$ROLE" --condition=None
done
```

## E. Redis on a free-tier e2-micro VM

```bash
ZONE=us-central1-a
REDIS_PASS=$(python3 -c "import secrets;print(secrets.token_urlsafe(24))")

# firewall: 6379 only from inside the VPC, only to VMs tagged "redis"
gcloud compute firewall-rules create allow-redis-internal \
  --project $PROJECT --network=default --direction=INGRESS --action=ALLOW \
  --rules=tcp:6379 --source-ranges=10.128.0.0/20 --target-tags=redis

# startup script: run Redis 7 in a container with AUTH + memory cap + LRU eviction
cat > /tmp/redis-startup.sh <<EOF
#!/bin/bash
docker rm -f redis 2>/dev/null || true
docker run -d --name redis --restart always -p 6379:6379 redis:7-alpine \
  redis-server --requirepass "${REDIS_PASS}" --maxmemory 200mb --maxmemory-policy allkeys-lru --appendonly no
EOF

# the VM (Container-Optimized OS has Docker preinstalled)
gcloud compute instances create redis-vm \
  --project $PROJECT --zone $ZONE --machine-type=e2-micro \
  --image-family=cos-stable --image-project=cos-cloud \
  --tags=redis --metadata-from-file=startup-script=/tmp/redis-startup.sh \
  --no-service-account --no-scopes
# -> INTERNAL_IP = 10.128.0.2

# store the connection string in Secret Manager (internal IP)
printf '%s' "redis://:${REDIS_PASS}@10.128.0.2:6379/0" | \
  gcloud secrets create REDIS_URL --project $PROJECT --data-file=- --replication-policy=automatic
gcloud secrets add-iam-policy-binding REDIS_URL --project $PROJECT \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/secretmanager.secretAccessor"
```

## F. Build the knowledge index (local, before deploy)

```bash
cd backend
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python scripts/ingest.py        # -> data/faiss_index/ (baked into the api image)
.venv/bin/python -m pytest tests/unit -q   # 27 passed
```

## G. Deploy to Cloud Run

```bash
# API (FastAPI) — Direct VPC egress so it can reach the Redis VM's private IP
gcloud run deploy api \
  --source backend --project $PROJECT --region $REGION \
  --service-account "$SA_EMAIL" \
  --network=default --subnet=default --vpc-egress=private-ranges-only \
  --set-secrets "REDIS_URL=REDIS_URL:latest" \
  --set-env-vars "GCP_PROJECT_ID=$PROJECT,GCP_LOCATION=$REGION,GEMINI_MODEL=gemini-2.5-flash,EMBEDDING_MODEL=text-embedding-005" \
  --memory 1Gi --cpu 1 --min-instances 0 --max-instances 2 --concurrency 20 --timeout 60 \
  --allow-unauthenticated

# grab the API URL, then deploy the Web (Next.js) pointed at it
API_URL=$(gcloud run services describe api --region $REGION --format='value(status.url)')
gcloud run deploy web \
  --source frontend --project $PROJECT --region $REGION \
  --set-env-vars "BACKEND_URL=${API_URL}" \
  --memory 512Mi --cpu 1 --min-instances 0 --max-instances 2 --concurrency 80 --timeout 60 \
  --allow-unauthenticated
```

## H. Smoke tests (post-deploy)

```bash
curl https://api-<hash>-uc.a.run.app/health          # {"status":"ok","kb_ready":true,"redis_ok":true,...}
curl -X POST https://web-<id>.us-central1.run.app/api/chat \
  -H 'content-type: application/json' -d '{"message":"Who is Brahim?"}'
```

## I. Updating later

```bash
# changed the bio?
cd backend && .venv/bin/python scripts/ingest.py
gcloud run deploy api --source backend --region $REGION ...   # same flags as above

# changed the UI?
gcloud run deploy web --source frontend --region $REGION ...
```

## Useful inspection / debug commands

```bash
gcloud run services list --region $REGION
gcloud run services describe api --region $REGION
gcloud compute instances list
gcloud compute ssh redis-vm --zone $ZONE       # then: docker logs redis
gcloud secrets versions access latest --secret=REDIS_URL   # (sensitive — be careful)
```
