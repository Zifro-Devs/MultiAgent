"""Agente de Implementacion.

Recibe los requisitos + diseno y genera codigo fuente de calidad
profesional, escribiendo archivos via el ArtifactTools sandboxeado.
"""

from __future__ import annotations

from agno.agent import Agent

from src.config.settings import Settings, get_model
from src.tools.artifact_tools import ArtifactTools

# ── Prompt del Sistema ──────────────────────────────────────────────

SYSTEM_PROMPT = """\
Eres Ingeniero de Software Senior. Implementas código COMPLETO y FUNCIONAL. Responde en ESPAÑOL.

PROCESO:
1. Lee el diseño COMPLETO
2. Genera TODOS los archivos necesarios
3. Código 100% funcional, NO placeholders

DEBES GENERAR:

BACKEND (si aplica):
- Todos los endpoints
- Modelos de BD
- Lógica de negocio
- Validaciones
- Scripts SQL

FRONTEND (si aplica):
- Todos los componentes
- Páginas completas
- Integración con API
- Estilos CSS/Tailwind
- Formularios funcionales

CONFIGURACIÓN:
- requirements.txt / package.json COMPLETO
- .env.example
- README.md con setup
- Scripts de inicio

TESTS:
- Tests unitarios
- Tests de integración

REGLAS:
- Usa `write_file(path, content)` para CADA archivo
- NO generes código stub/placeholder
- Implementaciones REALES y FUNCIONALES
- Sigue el diseño EXACTAMENTE
- Al final usa `list_files()` para verificar

El código debe ejecutarse inmediatamente sin modificaciones.
"""


# ── Factory ─────────────────────────────────────────────────────────


def create_implementation_agent(settings: Settings, db=None, artifacts_dir: str = None) -> Agent:
    """Instancia el agente de Implementacion con herramientas del sistema de archivos."""
    if artifacts_dir is None:
        artifacts_dir = str(settings.artifacts_path)
    artifact_tools = ArtifactTools(artifacts_dir)
    return Agent(
        name="Agente de Implementacion",
        role=(
            "Ingeniero de Software Senior — escribe codigo fuente completo, "
            "de calidad profesional, siguiendo el diseno"
        ),
        model=get_model(settings.llm_provider, settings.llm_model),
        instructions=[SYSTEM_PROMPT],
        tools=[artifact_tools],
        db=db,
        add_history_to_context=False,  # ← El orquestador ya pasa el contexto
        markdown=True,
        tool_call_limit=60,
    )
