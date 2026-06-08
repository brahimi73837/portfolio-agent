"""Retrieval over the FAISS knowledge base.

We expose a small wrapper so the rest of the app can:
  * embed a query once (and reuse that vector for the semantic cache), and
  * fetch the top-k relevant chunks to ground the answer.

The FAISS index is built offline by scripts/ingest.py and loaded once at startup.
"""
from __future__ import annotations

import logging

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_google_vertexai import VertexAIEmbeddings

from .config import get_settings

log = logging.getLogger("portfolio.retriever")

_embeddings: VertexAIEmbeddings | None = None
_retriever: "KnowledgeRetriever | None" = None


def get_embeddings() -> VertexAIEmbeddings:
    """Singleton Vertex AI embeddings client."""
    global _embeddings
    if _embeddings is None:
        s = get_settings()
        _embeddings = VertexAIEmbeddings(
            model_name=s.embedding_model,
            project=s.gcp_project_id,
            location=s.gcp_location,
        )
    return _embeddings


class KnowledgeRetriever:
    def __init__(self, store: FAISS):
        self._store = store

    def embed_query(self, text: str) -> list[float]:
        return get_embeddings().embed_query(text)

    def search_by_vector(self, vector: list[float], k: int | None = None) -> list[Document]:
        # MMR (maximal marginal relevance) instead of plain similarity: it diversifies
        # the retrieved chunks so broad questions ("his projects") surface DISTINCT
        # entries rather than several near-duplicate summary passages.
        k = k or get_settings().retriever_top_k
        return self._store.max_marginal_relevance_search_by_vector(
            vector, k=k, fetch_k=max(k * 4, 20), lambda_mult=0.5
        )

    @staticmethod
    def format_context(docs: list[Document]) -> str:
        """Join retrieved chunks into a single context block for the prompt."""
        return "\n\n---\n\n".join(d.page_content.strip() for d in docs)


def faiss_exists() -> bool:
    s = get_settings()
    return (s.faiss_path / "index.faiss").exists()


def get_retriever() -> KnowledgeRetriever:
    """Load the FAISS index once. Raises if it hasn't been built yet."""
    global _retriever
    if _retriever is None:
        s = get_settings()
        if not faiss_exists():
            raise FileNotFoundError(
                f"FAISS index not found at {s.faiss_path}. Run: python scripts/ingest.py"
            )
        store = FAISS.load_local(
            str(s.faiss_path),
            get_embeddings(),
            allow_dangerous_deserialization=True,  # we built this file ourselves
        )
        _retriever = KnowledgeRetriever(store)
        log.info("Loaded FAISS index from %s", s.faiss_path)
    return _retriever


def reset_retriever() -> None:
    """Test/ingest helper: force reload on next get_retriever()."""
    global _retriever
    _retriever = None
