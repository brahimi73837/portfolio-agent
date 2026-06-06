# 02 — Knowledge base & ingestion (RAG, part 1)

The bot only knows what's in the **knowledge base**. This chapter turns your bio into a searchable
vector index.

## What "RAG" means here

RAG = Retrieval-Augmented Generation. Instead of trusting the model's memory (which invents things), we:

1. **Embed** your bio into vectors (numbers that capture meaning).
2. Store them in a **vector index** (FAISS).
3. At question time, **retrieve** the few most relevant chunks and put them in the prompt.
4. The model answers **from those chunks** — grounded, not guessed.

## Step 1 — write your bio

Edit `backend/data/knowledge/brahim.md` (Markdown). You can also drop a `resume.pdf` in the same folder —
the ingester reads PDFs too. See [KNOWLEDGE_QUESTIONS.md](../KNOWLEDGE_QUESTIONS.md) for exactly what
recruiters ask; answer those in this file.

> Keep it public-safe: no home address, IDs, or anything private. The bot refuses sensitive questions,
> but the real safety is not storing sensitive data.

## Step 2 — run the ingester

```bash
cd backend
.venv/bin/python scripts/ingest.py
```

What it does ([`scripts/ingest.py`](../backend/scripts/ingest.py)):

- Loads every `.md` / `.txt` / `.pdf` in `data/knowledge/` (strips HTML comments so editor notes don't leak).
- **Chunks** the text with `RecursiveCharacterTextSplitter` (≈800 chars, 120 overlap) so each piece is
  small and self-contained, split on Markdown headings first.
- **Embeds** each chunk with Vertex AI `text-embedding-005` (768-dim vectors).
- Builds a **FAISS** index and saves it to `data/faiss_index/`.
- Writes `kb_version.txt` = a hash of the content. This version is part of every cache key, so **editing
  your bio and re-ingesting automatically invalidates stale cached answers** (no manual cache clearing).

Output looks like:

```
loaded brahim.md (2521 chars)
Split into 5 chunks. Embedding with text-embedding-005 ...
✅ Wrote FAISS index to .../data/faiss_index (kb_version=c444cef15086)
```

## Updating the knowledge base later

Just edit the file and re-run `python scripts/ingest.py`, then redeploy the `api` (the index is baked into
its container image — see [07](07-deploy-cloud-run.md)). The version bump handles cache invalidation.

## Why FAISS (not a hosted vector DB)?

For a single resume, a hosted vector database is overkill and adds cost + a network hop. FAISS is an
in-process library — the index is a file we load at startup. Zero infrastructure, sub-millisecond search,
$0. If the knowledge base ever grew huge, we'd revisit this.

Next: [03 — Backend: LangChain RAG](03-backend-langchain-rag.md).
