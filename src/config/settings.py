"""Centralised application settings.

Reads from environment variables and ``.env`` file using *pydantic-settings*.
All secrets stay in ``.env`` — never hard-coded.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


# ── Settings Model ──────────────────────────────────────────────────


class Settings(BaseSettings):
    """Application-wide configuration.

    Values are loaded in order of precedence:
    1. Explicit environment variables
    2. ``.env`` file in the project root
    3. Defaults defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ────────────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_provider: Literal["openai", "anthropic", "google", "ollama"] = "ollama"
    llm_model: str = "qwen3:4b"
    orchestrator_model: str = "qwen3:4b"
    ollama_host: str = "http://localhost:11434"

    # ── Database ───────────────────────────────────────────────────
    supabase_db_url: str = ""

    # ── Artifacts ──────────────────────────────────────────────────
    artifacts_dir: str = "artifacts"

    # ── Application ────────────────────────────────────────────────
    app_name: str = "DevTeam AI"
    debug: bool = False

    # ── Derived paths ──────────────────────────────────────────────
    @property
    def project_root(self) -> Path:
        """Return the top-level project directory."""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def artifacts_path(self) -> Path:
        """Return *resolved* artifacts directory (auto-created)."""
        path = self.project_root / self.artifacts_dir
        path.mkdir(parents=True, exist_ok=True)
        return path


# ── Singleton accessor ──────────────────────────────────────────────


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings instance."""
    return Settings()


# ── Model factory ───────────────────────────────────────────────────


def get_model(
    provider: Optional[str] = None,
    model_id: Optional[str] = None,
):
    """Instantiate an Agno model for the requested provider.

    Falls back to values in ``Settings`` when arguments are ``None``.
    """
    cfg = get_settings()
    provider = provider or cfg.llm_provider
    model_id = model_id or cfg.llm_model

    if provider == "openai":
        from agno.models.openai import OpenAIChat

        return OpenAIChat(id=model_id)

    if provider == "anthropic":
        from agno.models.anthropic import Claude

        return Claude(id=model_id)

    if provider == "google":
        from agno.models.google import Gemini

        return Gemini(id=model_id)

    if provider == "ollama":
        from agno.models.ollama import Ollama

        host = cfg.ollama_host.strip() if cfg.ollama_host else ""
        return Ollama(id=model_id, host=host or None)

    raise ValueError(f"Unsupported LLM provider: {provider!r}")
