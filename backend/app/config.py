"""Central configuration, loaded from environment / .env.

Every tunable lives here so the rest of the code never reads os.environ directly.
This keeps behaviour predictable and makes the cost/abuse knobs easy to find.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Absolute path to the backend/ directory (parent of app/).
BACKEND_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Vertex AI ---
    gcp_project_id: str = "portfolio-agent-499115"
    gcp_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "text-embedding-005"
    google_application_credentials: str | None = None

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Generation ---
    max_output_tokens: int = 512
    temperature: float = 0.3
    thinking_budget: int = 0

    # --- Retrieval ---
    retriever_top_k: int = 4
    kb_dir: str = "data/knowledge"
    faiss_dir: str = "data/faiss_index"

    # --- Caching ---
    response_cache_ttl_seconds: int = 86_400
    semantic_cache_threshold: float = 0.92
    semantic_cache_enabled: bool = True

    # --- Abuse / cost guards ---
    rate_limit_per_minute: int = 8
    rate_limit_per_day_per_ip: int = 60
    global_daily_request_cap: int = 800
    max_input_chars: int = 1000

    # --- App ---
    cors_allow_origins: str = "*"
    log_level: str = "INFO"

    # --- Derived paths (absolute) ---
    @property
    def kb_path(self) -> Path:
        return BACKEND_ROOT / self.kb_dir

    @property
    def faiss_path(self) -> Path:
        return BACKEND_ROOT / self.faiss_dir

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so we parse the environment exactly once."""
    return Settings()
