# MANUAL SETUP — the parts only you (a human) can do

This is your checklist. Everything here needs a human: clicking in consoles, creating accounts, pasting
secrets, writing facts about yourself. Do these in order. When a step says **➡️ give me X**, paste that value
back to me (Claude) — but **never paste real secret values into the chat**; put secrets in the local `.env`
files I'll create and just tell me "done". For non-secret values (project ID, region, URLs) pasting is fine.

> Legend: 🟢 = required for local dev · 🔵 = required for deploy · ⏱️ rough time.

---

## 0. Accounts you need (🟢🔵, ⏱️ 10 min)

| Account | Why | Link |
|---|---|---|
| Google account | Gemini API key + Google Cloud | — |
| Google AI Studio | Free Gemini API key (generation + embeddings) | https://aistudio.google.com/apikey |
| Google Cloud (with credits/billing) | Cloud Run, VM, Secret Manager | https://console.cloud.google.com |
| GitHub | Host the repo | https://github.com |

You said you have Google Cloud credits — make sure **billing is enabled** on the project (credits still
require an active billing account; you won't be charged while credits last and our caps keep usage tiny).

---

## 1. Get your Gemini API key (🟢, ⏱️ 2 min)

1. Go to https://aistudio.google.com/apikey
2. Click **Create API key** → pick (or create) a project → copy the key (`AIza...`).
3. Keep it. We'll use the **Gemini API** (AI Studio) free tier, *not* Vertex AI — it's the zero-cost path.

**➡️ give me:** just say "I have the Gemini key" (you'll paste it into `.env`, not the chat).

Free-tier sanity: Gemini 2.5 Flash and `gemini-embedding-001` both have a free tier with low rate limits.
Our caching + daily cap keep us inside it. If you ever see quota errors, that's the limiter working, not a bug.

---

## 2. Write your knowledge base (🟢, ⏱️ 30–60 min) — the most important human step

The bot is only as good as this. You have two options (you can do both):

**Option A — Text (recommended, easiest to edit):** create `backend/data/knowledge/brahim.md`.
**Option B — PDF:** drop your resume PDF in `backend/data/knowledge/` (e.g. `resume.pdf`). The ingest
script reads PDFs too.

Write in plain language, first or third person, organized by topic. Cover:

- **Snapshot**: name, current role/title, location (city/region is fine — *no street address*), years of
  experience, what you're looking for (roles, full-time/contract, remote).
- **Skills**: languages, frameworks, cloud, AI/ML tools — grouped, honest about levels.
- **Projects**: 3–6 projects. For each: what it does, your role, the stack, the impact/result, a link if public.
  (Include *this* chatbot as a project — it's a great talking point.)
- **Experience**: roles, companies, dates, what you achieved (bullet results, numbers if you have them).
- **Education / certs**.
- **Achievements / highlights**: awards, OSS, talks, notable numbers.
- **FAQ for recruiters**: "Are you open to relocation?", "What's your visa/work-authorization status?"
  (only what you're comfortable being public), "What kind of role are you after?", "How can I contact you?"
  (a professional email / LinkedIn — your call).

**Do NOT put in here:** anything you wouldn't want a stranger to read — home address, government IDs,
exact salary expectations if private, personal/family info, passwords. The bot will also refuse sensitive
questions, but the real safety is not putting sensitive data in at all.

Tip: write a clear **contact line** and a one-paragraph **"about Brahim" intro** — the bot will lean on these.

**➡️ give me:** the file(s) in `backend/data/knowledge/`, or just paste the text and I'll save it. Tell me
which contact info (if any) is OK to share publicly.

---

## 3. Create the GitHub repo (🔵, ⏱️ 3 min)

1. https://github.com/new → name it (e.g. `portfolio-agent`) → **Private** is fine → create.
2. Don't add a README/.gitignore (we have them).
3. Copy the remote URL (`https://github.com/<you>/portfolio-agent.git`).

**➡️ give me:** the repo URL. (Optional — install `gh` CLI: `brew install gh && gh auth login` so I can push
for you. Otherwise I'll give you the exact `git push` commands.)

---

## 4. Set up the Google Cloud project & CLI (🔵, ⏱️ 15 min)

### 4a. Install the gcloud CLI (on your Mac)
```bash
brew install --cask google-cloud-sdk      # or: https://cloud.google.com/sdk/docs/install
gcloud init                               # login + pick/create a project
gcloud auth login
gcloud auth application-default login
```

### 4b. Create / pick a project and set it
```bash
# create new (or skip and use an existing one):
gcloud projects create brahim-portfolio-<random> --name="Brahim Portfolio"
gcloud config set project <YOUR_PROJECT_ID>
gcloud config set run/region us-central1     # free-tier-eligible region for the VM too
```

### 4c. Link billing (credits live here)
- Console → **Billing** → link your billing account (the one with credits) to this project.
- Verify: `gcloud beta billing projects describe <YOUR_PROJECT_ID>` shows `billingEnabled: true`.

### 4d. Enable the APIs we use
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com
```

**➡️ give me:** your `PROJECT_ID` and the `REGION` you used (these aren't secret). Confirm billing is enabled.

---

## 5. Store secrets in Secret Manager (🔵, ⏱️ 5 min) — *do this with me, after I scaffold*

We'll run this together once code exists, but here's what will be stored (so you know what to have ready):

- `GEMINI_API_KEY` — from step 1.
- `REDIS_URL` — produced in step 6 (looks like `redis://:PASSWORD@<VM_INTERNAL_IP>:6379/0`).

Command pattern (I'll give exact values later):
```bash
printf '%s' "AIza...yourkey..." | gcloud secrets create GEMINI_API_KEY --data-file=- --replication-policy=automatic
printf '%s' "redis://:PASS@IP:6379/0" | gcloud secrets create REDIS_URL --data-file=-
```

**➡️ nothing yet** — we do this in Phase 2.

---

## 6. The Redis VM (🔵, ⏱️ 10 min) — *I'll generate the exact commands; you run them*

We'll create one **`e2-micro`** VM (free-tier eligible in `us-central1`/`us-west1`/`us-east1`) running Redis in
Docker, locked down to only accept connections from Cloud Run, password-protected. I provide a `cloud-init`
file and the `gcloud compute instances create ...` command in `docs/06-redis-vm.md`. You'll run it and paste
me back the VM's internal IP. **No Redis data is sensitive**, but we still set a password and firewall it.

**➡️ later:** run my command, give me the VM internal IP; put the generated `REDIS_URL` into `.env` / Secret Manager.

---

## 7. What I need from you to start building (the short list)

Paste these back when ready (secrets go in files, not chat):

1. ✅ "Gemini key ready" (in `backend/.env` as `GEMINI_API_KEY=...` once I create the file).
2. 📄 Your knowledge-base content (file or pasted text) + which contact info is public-OK.
3. 🌐 GitHub repo URL (and whether `gh` is installed).
4. ☁️ `PROJECT_ID` + `REGION`, billing enabled confirmed.
5. 🎛️ Any preferences: bot's display name/tone, accent color, the 3–4 suggested questions to show.

Steps 4–6 (cloud + VM + deploy) can come *after* we have it working locally — we don't need them to build
and test the core. So the fastest path to a running local demo is just **#1 and #2**.

---

## Cost guardrails (so you can relax about credits)

- Cloud Run: scales to **zero** when idle → you pay nothing between visits; generous free tier when active.
- One `e2-micro` VM: **free tier** (1/month in eligible US regions).
- Gemini API: **free tier**, further protected by response caching + a hard **daily request cap** in the app.
- Artifact Registry / Secret Manager: pennies-or-free at this scale, covered by credits.
- The app **refuses to call paid APIs once the daily cap is hit** — a runaway loop or abuser cannot drain credits.

If anything in here is unclear, tell me which step and I'll expand it.
