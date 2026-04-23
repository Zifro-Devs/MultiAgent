"""Orquestador del Equipo de Desarrollo - Versión Optimizada.

Sistema experto que guía al usuario con preguntas contextuales,
adaptativas y profesionales, integrando memoria vectorizada para
sugerir requisitos basados en proyectos similares.

OPTIMIZADO para reducir uso de tokens sin sacrificar funcionalidad.
"""

from __future__ import annotations

from typing import Optional

from agno.team import Team, TeamMode

from src.agents.analysis import create_analysis_agent
from src.agents.design import create_design_agent
from src.agents.implementation import create_implementation_agent
from src.agents.validation import create_validation_agent
from src.config.settings import Settings, get_model, get_settings
from src.storage.database import get_database
from src.utils.document_compressor import (
    extract_requirements_summary,
    extract_design_essentials,
    get_compression_stats
)

# ── Instrucciones del Orquestador (Optimizadas) ────────────────────

ORCHESTRATOR_INSTRUCTIONS = [
    """\
Eres Líder de Equipo de Desarrollo. Responde en ESPAÑOL.

PROCESO AUTOMÁTICO:

1. Haz 2-3 preguntas específicas sobre el proyecto
2. Cuando tengas suficiente información (>80%), di EXACTAMENTE:

"EJECUTAR_PIPELINE:[nombre-proyecto]"

Donde [nombre-proyecto] es formato kebab-case (ej: pagina-apple, api-usuarios)

3. El sistema ejecutará automáticamente: Análisis → Diseño → Código → Validación

NO pidas confirmación. NO preguntes si comenzar. Cuando tengas la info, ejecuta automáticamente.

Ejemplo:
Usuario: "Quiero una página de Apple"
Tú: "¿Qué información mostrarás? ¿Quiénes son los usuarios? ¿Necesitas formularios?"
Usuario: [responde]
Tú: "EJECUTAR_PIPELINE:pagina-apple"
"""
]


# ── Factory ─────────────────────────────────────────────────────────


def create_dev_team(
    overrides: Optional[dict] = None,
    session_id: Optional[str] = None,
    project_name: Optional[str] = None,  # Nuevo parámetro
) -> Team:
    """Construye equipo de desarrollo con compresión de documentos."""
    settings = get_settings()
    if overrides:
        settings = settings.model_copy(update=overrides)

    db = get_database(settings)
    
    # Si hay nombre de proyecto, crear carpeta específica
    if project_name:
        project_artifacts_path = settings.artifacts_path / project_name
        project_artifacts_path.mkdir(parents=True, exist_ok=True)
        artifacts_dir = str(project_artifacts_path)
    else:
        artifacts_dir = str(settings.artifacts_path)

    # Crear agentes especializados con la ruta específica del proyecto
    analysis = create_analysis_agent(settings, db)
    design = create_design_agent(settings, db)
    implementation = create_implementation_agent(settings, db, artifacts_dir)
    validation = create_validation_agent(settings, db, artifacts_dir)

    # Ensamblar equipo CON miembros
    team = Team(
        name="DevTeam AI",
        model=get_model(settings.llm_provider, settings.orchestrator_model),
        members=[analysis, design, implementation, validation],
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        db=db,
        add_history_to_context=True,
        add_datetime_to_context=False,
        markdown=True,
        session_id=session_id,
    )
    
    return team

