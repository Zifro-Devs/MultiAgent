"""Agente de Testing (TDD-oriented).

Genera la suite de tests a partir de los criterios de aceptación definidos
en los requisitos, no post-mortem sobre el código. Escribe tests unitarios,
de integración y E2E (cuando aplica) adaptados al stack del proyecto.
"""

from __future__ import annotations

from typing import Optional

from agno.agent import Agent

from src.agents.prompts.testing import TESTING_PROMPT
from src.config.settings import Settings, get_model
from src.tools.artifact_tools import ArtifactTools


def create_testing_agent(
    settings: Settings,
    db=None,
    artifacts_dir: Optional[str] = None,
) -> Agent:
    """Construye el agente de testing."""
    if artifacts_dir is None:
        artifacts_dir = str(settings.artifacts_path)

    artifact_tools = ArtifactTools(artifacts_dir)

    return Agent(
        name="Agente de Testing",
        role=(
            "Staff SDET — produce suites de prueba basadas en criterios "
            "de aceptación, con cobertura unit/integration/e2e"
        ),
        model=get_model(settings.llm_provider, settings.llm_model),
        instructions=[TESTING_PROMPT],
        tools=[artifact_tools],
        db=db,
        add_history_to_context=False,
        markdown=True,
        tool_call_limit=60,
    )
