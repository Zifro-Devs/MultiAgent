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
    openai_api_base: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    llm_provider: Literal["openai", "anthropic", "google", "ollama", "groq"] = "ollama"
    llm_model: str = "qwen3:4b"
    orchestrator_model: str = "qwen3:4b"
    ollama_host: str = "http://localhost:11434"
    default_model: str = ""  # Para OpenRouter

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
        """Return *resolved* artifacts directory (auto-created).
        
        Soporta rutas absolutas y relativas:
        - Relativa: "artifacts" → project_root/artifacts
        - Absoluta: "C:/Users/..." → usa la ruta tal cual
        """
        artifacts_dir = self.artifacts_dir.strip()
        
        # Si es ruta absoluta, usarla directamente
        path = Path(artifacts_dir)
        if path.is_absolute():
            path.mkdir(parents=True, exist_ok=True)
            return path
        
        # Si es relativa, usar desde project_root
        path = self.project_root / artifacts_dir
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
    model_id = model_id or cfg.llm_model or cfg.default_model

    if provider == "openai":
        from agno.models.openai import OpenAIChat

        # Si hay OPENAI_API_BASE configurado, es OpenRouter
        if cfg.openai_api_base:
            logger.info(f"Using OpenRouter with model: {model_id}")
            return OpenAIChat(
                id=model_id,
                api_key=cfg.openai_api_key,
                base_url=cfg.openai_api_base,
                max_tokens=4096  # Límite razonable para evitar errores de créditos
            )
        else:
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

    if provider == "groq":
        from agno.models.groq import Groq

        return Groq(
            id=model_id,
            api_key=cfg.groq_api_key,
            max_tokens=4096
        )

    raise ValueError(f"Unsupported LLM provider: {provider!r}")
