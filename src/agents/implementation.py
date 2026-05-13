"""Agente de Implementación.

Ahora es una factory adaptativa: recibe un StackProfile (o un prompt
explícito) y construye el agente con el system prompt especializado para
ese stack. El prompt se selecciona desde el módulo de prompts curados.
"""

from __future__ import annotations

from typing import Optional

from agno.agent import Agent

from src.agents.prompts.fullstack import FULLSTACK_PROMPT
from src.agents.prompts.selector import StackProfile, select_implementation_prompt
from src.config.settings import Settings, get_model
from src.tools.artifact_tools import ArtifactTools


def create_implementation_agent(
    settings: Settings,
    db=None,
    artifacts_dir: Optional[str] = None,
    profile: Optional[StackProfile] = None,
    prompt_override: Optional[str] = None,
) -> Agent:
    """Construye el agente de implementación con prompt adaptativo al stack.

    Args:
        settings: configuración global.
        db: base de datos de sesiones de Agno (opcional).
        artifacts_dir: carpeta sandbox donde se escriben los archivos.
        profile: stack detectado del diseño. Si None, se usa el prompt
            fullstack como fallback seguro.
        prompt_override: si se especifica, se usa este prompt literal y se
            ignora el profile. Útil para pruebas o modos custom.
    """
    if artifacts_dir is None:
        artifacts_dir = str(settings.artifacts_path)

    artifact_tools = ArtifactTools(artifacts_dir)

    if prompt_override is not None:
        system_prompt = prompt_override
    elif profile is not None:
        system_prompt = select_implementation_prompt(profile)
    else:
        # Fallback: fullstack es el más general
        system_prompt = FULLSTACK_PROMPT

    return Agent(
        name="Agente de Implementación",
        role=(
            "Staff Engineer — escribe código de producción siguiendo el "
            "contrato del diseño"
        ),
        model=get_model(settings.llm_provider, settings.llm_model),
        instructions=[system_prompt],
        tools=[artifact_tools],
        db=db,
        add_history_to_context=False,
        markdown=True,
        tool_call_limit=80,
    )
