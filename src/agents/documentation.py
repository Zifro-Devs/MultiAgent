"""Agente de Documentación.

Produce README, ARCHITECTURE, CONTRIBUTING y PROYECTO basándose en el
código real generado. Usa el prompt enriquecido del módulo de prompts.
"""

from __future__ import annotations

from typing import Optional

from agno.agent import Agent

from src.agents.prompts.documentation import DOCUMENTATION_PROMPT
from src.config.settings import Settings, get_model
from src.tools.artifact_tools import ArtifactTools


def create_documentation_agent(
    settings: Settings,
    artifacts_dir: Optional[str] = None,
) -> Agent:
    """Construye el agente de documentación."""
    if artifacts_dir is None:
        artifacts_dir = str(settings.artifacts_path)

    artifact_tools = ArtifactTools(artifacts_dir)

    return Agent(
        name="Agente de Documentación",
        role="Principal Technical Writer — documentación específica, útil y profesional",
        model=get_model(settings.llm_provider, settings.llm_model),
        instructions=[DOCUMENTATION_PROMPT],
        tools=[artifact_tools],
        add_history_to_context=False,
        markdown=True,
        tool_call_limit=50,
    )
