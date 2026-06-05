#!/usr/bin/env python3
"""Build the FAISS knowledge base from documents in data/knowledge/.

Pipeline:  load (.md/.txt/.pdf) -> clean -> chunk -> embed (Vertex AI) -> FAISS index.
Also stamps data/faiss_index/kb_version.txt with a content hash so that updating the
knowledge base automatically invalidates stale cached answers.

Usage (from backend/):  python scripts/ingest.py
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

# Make `app` importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document  # noqa: E402
from langchain_community.vectorstores import FAISS  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.retriever import get_embeddings  # noqa: E402

_HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def _read_text_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    # Strip HTML comments (e.g. the "REPLACE ME" notes) so they don't enter the KB.
    return _HTML_COMMENT.sub("", text)


def _read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def load_documents(kb_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(kb_dir.iterdir()):
        if path.name.startswith("."):
            continue
        suffix = path.suffix.lower()
        if suffix in (".md", ".txt"):
            content = _read_text_file(path)
        elif suffix == ".pdf":
            content = _read_pdf(path)
        else:
            continue
        if content.strip():
            docs.append(Document(page_content=content, metadata={"source": path.name}))
            print(f"  loaded {path.name} ({len(content)} chars)")
    return docs


def content_hash(docs: list[Document]) -> str:
    h = hashlib.sha256()
    for d in docs:
        h.update(d.page_content.encode("utf-8"))
    return h.hexdigest()[:12]


def main() -> int:
    s = get_settings()
    kb_dir = s.kb_path
    out_dir = s.faiss_path
    print(f"Knowledge dir: {kb_dir}")

    if not kb_dir.exists():
        print(f"ERROR: knowledge dir {kb_dir} does not exist", file=sys.stderr)
        return 1

    docs = load_documents(kb_dir)
    if not docs:
        print("ERROR: no .md/.txt/.pdf documents found to ingest", file=sys.stderr)
        return 1

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=120,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks. Embedding with {s.embedding_model} ...")

    store = FAISS.from_documents(chunks, get_embeddings())
    out_dir.mkdir(parents=True, exist_ok=True)
    store.save_local(str(out_dir))

    version = content_hash(docs)
    (out_dir / "kb_version.txt").write_text(version)
    print(f"✅ Wrote FAISS index to {out_dir} (kb_version={version})")
    print("   Re-run this whenever you edit the knowledge base.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
