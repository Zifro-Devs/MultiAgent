"""Agente de Diseño de Sistemas.

Produce documentos de arquitectura completos con diagramas Mermaid, ADRs
y un contrato de implementación estructurado que el siguiente agente puede
seguir sin improvisar decisiones.
"""

from __future__ import annotations

from agno.agent import Agent

from src.agents.prompts.design import DESIGN_PROMPT
from src.config.settings import Settings, get_model


def create_design_agent(settings: Settings, db=None) -> Agent:
    """Construye el agente de diseño con prompt enriquecido."""
    return Agent(
        name="Agente de Diseño",
        role=(
            "Staff Software Architect — diseña sistemas completos con "
            "contratos explícitos de implementación"
        ),
        model=get_model(settings.llm_provider, settings.llm_model),
        instructions=[DESIGN_PROMPT],
        db=db,
        add_history_to_context=False,
        markdown=True,
    )
