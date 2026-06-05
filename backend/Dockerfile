# Backend: FastAPI + LangChain + Vertex AI. Runs on Cloud Run.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt .
RUN pip install -r requirements.txt

# App code + the prebuilt FAISS index + knowledge base.
COPY app ./app
COPY scripts ./scripts
COPY data ./data

# Cloud Run provides $PORT (default 8080).
ENV PORT=8080
EXPOSE 8080

# Single worker: the in-memory FAISS index + caches live per process; low traffic.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1
