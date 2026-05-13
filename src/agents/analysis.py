"""Agente de Análisis de Requisitos.

Genera especificaciones IEEE 830 completas con criterios de aceptación
testables, trazabilidad explícita y modelado de personas. Usa el prompt
mejorado del módulo de prompts especializados.
"""

from __future__ import annotations

from agno.agent import Agent

from src.agents.prompts.analysis import ANALYSIS_PROMPT
from src.config.settings import Settings, get_model


def create_analysis_agent(settings: Settings, db=None) -> Agent:
    """Construye el agente de análisis con el prompt optimizado."""
    return Agent(
        name="Agente de Análisis",
        role=(
            "Arquitecto de Soluciones y Analista de Negocio Senior — "
            "produce especificaciones IEEE 830 testables y trazables"
        ),
        model=get_model(settings.llm_provider, settings.llm_model),
        instructions=[ANALYSIS_PROMPT],
        db=db,
        add_history_to_context=False,
        markdown=True,
    )
