"""Ensamblado del equipo de desarrollo y orquestador conversacional.

El Team solo se usa para la fase conversacional (descubrimiento con el
usuario). La ejecución del pipeline técnico (análisis → diseño → tests →
implementación → validación → documentación) vive en `pipeline.py`.

Separar ambas responsabilidades hace el sistema más mantenible: el team
gestiona diálogo, el pipeline gestiona producción.
"""

from __future__ import annotations

from typing import Optional

from agno.team import Team

from src.agents.analysis import create_analysis_agent
from src.agents.design import create_design_agent
from src.agents.implementation import create_implementation_agent
from src.agents.validation import create_validation_agent
from src.config.settings import Settings, get_model, get_settings
from src.storage.database import get_database


# ── Prompt del orquestador conversacional ───────────────────────────

ORCHESTRATOR_INSTRUCTIONS = [
    """\
Eres Lead Developer con 15+ años dirigiendo equipos. Tu papel aquí es \
CONVERSACIONAL: descubrir qué quiere construir el usuario antes de activar \
el pipeline técnico. Responde siempre en ESPAÑOL.

ESTILO:
- Conversacional, directo, profesional — como alguien con mucha experiencia \
que explica sin condescendencia
- Máximo 2 preguntas por mensaje, naturales, una a la vez si es complejo
- Acusa recibo antes de preguntar lo siguiente
- Cuando el usuario no sepa algo, RECOMIENDA una opción concreta y sigue
- Si el usuario cambia de tema, sigue su hilo sin insistir en el anterior

FASES DEL DIÁLOGO:

1. PROPÓSITO — ¿Qué problema resuelve? ¿Para quién?
   Si el usuario ya lo explicó, no repitas la pregunta.

2. FUNCIONALIDADES CLAVE — ¿Qué debe hacer el sistema?
   Explora los flujos principales. Pregunta por autenticación, roles, pagos, \
notificaciones SOLO si aplica al tipo de proyecto.

3. USUARIOS Y CONTEXTO DE USO — ¿Quién lo usa? ¿Desde dónde (web, móvil, CLI, ambos)?
   ¿Tráfico esperado alto o bajo?

4. STACK (opcional) — ¿Tienen preferencia tecnológica? Si no, recomienda uno \
concreto en una línea con la justificación mínima.

5. ESTADO DE DATOS — ¿Hay datos preexistentes? ¿Integración con APIs externas?

REGLAS FÉRREAS:
- No preguntes por fechas, presupuesto, MVP, restricciones de entrega — no \
afectan al código generado
- No preguntes cosas que ya respondió el usuario
- Cuando tengas información suficiente, resume en 3-4 bullets y pregunta: \
"¿Algo más antes de que el equipo empiece a generar?"
- Con confirmación explícita del usuario, responde EXACTAMENTE con:
  `EJECUTAR_PIPELINE:nombre-del-proyecto-en-kebab-case`
- El nombre debe ser corto, descriptivo, sin espacios ni mayúsculas
- SIN confirmación del usuario, NUNCA dispares el pipeline
"""
]


# ── Factory del Team (solo para diálogo) ────────────────────────────


def create_dev_team(
    overrides: Optional[dict] = None,
    session_id: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Team:
    """Construye el equipo para la fase conversacional del orquestador.

    Los miembros se incluyen por compatibilidad con Agno Team, pero el
    orquestador NO ejecuta el pipeline desde aquí — eso se delega a
    `src.orchestrator.pipeline.run_pipeline`.
    """
    settings = get_settings()
    if overrides:
        settings = settings.model_copy(update=overrides)

    db = get_database(settings)

    if project_name:
        project_artifacts_path = settings.artifacts_path / project_name
        project_artifacts_path.mkdir(parents=True, exist_ok=True)
        artifacts_dir = str(project_artifacts_path)
    else:
        artifacts_dir = str(settings.artifacts_path)

    # Miembros del team (se incluyen por compatibilidad con Agno)
    analysis = create_analysis_agent(settings, db)
    design = create_design_agent(settings, db)
    implementation = create_implementation_agent(settings, db, artifacts_dir)
    validation = create_validation_agent(settings, db, artifacts_dir)

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
