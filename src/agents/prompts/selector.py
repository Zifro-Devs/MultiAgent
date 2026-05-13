"""Selector de prompts según el stack detectado.

Recibe el tipo de proyecto y el stack primario, y devuelve el prompt de
implementación y testing más adecuados. Si no hay match exacto, cae al
prompt genérico fullstack como fallback seguro.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.agents.prompts.backend import (
    BACKEND_NODE_PROMPT,
    BACKEND_FASTAPI_PROMPT,
    BACKEND_DJANGO_PROMPT,
    BACKEND_GO_PROMPT,
)
from src.agents.prompts.frontend import (
    FRONTEND_REACT_PROMPT,
    FRONTEND_NEXTJS_PROMPT,
    FRONTEND_VUE_PROMPT,
)
from src.agents.prompts.fullstack import FULLSTACK_PROMPT
from src.agents.prompts.mobile import MOBILE_RN_PROMPT
from src.agents.prompts.cli import CLI_PROMPT
from src.agents.prompts.data import DATA_PROMPT
from src.agents.prompts.testing import TESTING_PROMPT


@dataclass(frozen=True)
class StackProfile:
    """Perfil normalizado del stack detectado a partir del diseño."""

    project_type: str                  # api_rest | web_app | fullstack | ...
    language: str                      # python | typescript | go | ...
    backend_framework: Optional[str]   # fastapi | express | django | ...
    frontend_framework: Optional[str]  # react_vite | nextjs | vue3 | ...
    database: Optional[str]            # postgresql | mysql | mongodb | ...

    @property
    def has_backend(self) -> bool:
        return bool(self.backend_framework)

    @property
    def has_frontend(self) -> bool:
        return bool(self.frontend_framework)


def select_implementation_prompt(profile: StackProfile) -> str:
    """Selecciona el prompt de implementación más específico al stack."""
    ptype = (profile.project_type or "").lower()
    bf = (profile.backend_framework or "").lower()
    ff = (profile.frontend_framework or "").lower()

    # Proyectos especializados
    if ptype in {"mobile_app", "mobile"}:
        return MOBILE_RN_PROMPT
    if ptype in {"cli_tool", "cli"}:
        return CLI_PROMPT
    if ptype in {"data_pipeline", "ml_model", "data"}:
        return DATA_PROMPT

    # Fullstack tiene prioridad cuando hay ambos
    if profile.has_backend and profile.has_frontend:
        return FULLSTACK_PROMPT

    # Solo frontend
    if profile.has_frontend and not profile.has_backend:
        if "next" in ff:
            return FRONTEND_NEXTJS_PROMPT
        if "vue" in ff:
            return FRONTEND_VUE_PROMPT
        return FRONTEND_REACT_PROMPT

    # Solo backend
    if profile.has_backend and not profile.has_frontend:
        if "fastapi" in bf:
            return BACKEND_FASTAPI_PROMPT
        if "django" in bf:
            return BACKEND_DJANGO_PROMPT
        if "express" in bf or "fastify" in bf or "nest" in bf:
            return BACKEND_NODE_PROMPT
        if bf in {"chi", "gin", "echo", "fiber", "go"}:
            return BACKEND_GO_PROMPT
        # Default backend si el lenguaje es python
        if profile.language == "python":
            return BACKEND_FASTAPI_PROMPT
        if profile.language == "typescript" or profile.language == "javascript":
            return BACKEND_NODE_PROMPT

    # Fallback: fullstack es el más general y cubre estructura completa
    return FULLSTACK_PROMPT


def select_testing_prompt(profile: StackProfile) -> str:
    """Por ahora el prompt de testing es único — ya cubre múltiples stacks internamente."""
    return TESTING_PROMPT
