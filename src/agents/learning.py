"""Agente de Aprendizaje Continuo.

A diferencia de la versión anterior, que solo aprendía al terminar un proyecto,
este agente extrae conocimiento de MÚLTIPLES SEÑALES a lo largo del ciclo:

  1. Completion signal    — al terminar un proyecto exitosamente.
  2. Failure signal       — cuando un quality gate falla repetidamente.
  3. Compiler signal      — cuando el code validator detecta errores recurrentes.
  4. Validation signal    — hallazgos reales del agente de validación.
  5. User preference      — del diálogo con el usuario (stacks, naming, estilos).

Cada señal produce insights que se almacenan con `source_signal` apropiado.
Los insights se deduplicar, refuerzan o archivan automáticamente.

Además expone feedback hooks que el pipeline invoca:

  - `mark_used_insights_success(ids)`  → refuerza los insights que se
     inyectaron al diseño/implementación si el proyecto terminó sin gates
     fallidos ni errores de compilación.
  - `mark_used_insights_failure(ids)`  → penaliza los insights si el
     proyecto falló (algo de lo recomendado resultó contraproducente).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from src.config.settings import Settings, get_model
from src.storage.knowledge_memory import KNOWLEDGE_CATEGORIES, KnowledgeMemory

logger = logging.getLogger(__name__)


# ── Prompt base para extracción de insights ─────────────────────────

_BASE_EXTRACTION_PROMPT = """\
Eres un sistema de aprendizaje autónomo. Tu único trabajo es analizar \
evidencia de un proyecto de software y extraer conocimiento reutilizable.

NO eres un asistente. NO conversas. SOLO produces JSON.

CATEGORÍAS DISPONIBLES:
- patron_exitoso: algo que funcionó bien y vale repetir
- anti_patron: algo que causó problemas, evitar
- preferencia_usuario: lo que el usuario pidió explícitamente
- decision_tecnica: stack, librerías, arquitecturas que funcionaron
- solucion_problema: cómo se resolvió un problema específico
- estructura_proyecto: organización de código exitosa
- integracion: APIs/servicios que se implementaron bien
- error_comun: errores frecuentes y cómo evitarlos
- error_compilador: patrones que el compilador/linter rechaza
- hallazgo_validacion: problemas reales detectados en auditoría
- falla_quality_gate: patrones que hacen fallar gates de calidad
- convencion_nombres: naming patterns preferidos por el usuario

REGLAS:
1. Solo conocimiento CONCRETO y ACCIONABLE. No generalidades vagas.
2. Específico: "usar JWT con refresh tokens de 30 días en APIs REST" es bueno. \
"usar autenticación" es inútil.
3. Si no hay nada valioso, devuelve {"insights": []}
4. Máximo 8 insights por llamada, los MÁS valiosos.
5. Formato de salida OBLIGATORIO: JSON puro, sin markdown, sin texto adicional.

FORMATO DE RESPUESTA:
{
  "insights": [
    {
      "category": "patron_exitoso",
      "title": "Título corto (≤80 chars)",
      "insight": "Conocimiento concreto y accionable (≤300 chars)",
      "project_type": "web|api|fullstack|mobile|cli|data|ml|desktop",
      "tags": ["tag1", "tag2"]
    }
  ]
}
"""


# ── Estructura de datos ──────────────────────────────────────────────


@dataclass
class LearningSignal:
    """Una señal de aprendizaje con sus datos crudos."""

    signal_type: str  # completion | failure | compiler | validation | user_pref
    project_name: str
    project_type: str
    payload: str  # Texto crudo con la evidencia


@dataclass
class LearningBatch:
    """Conjunto de señales a procesar en una llamada al LLM."""

    signals: List[LearningSignal] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.signals

    def render_for_extraction(self) -> str:
        """Compone el input al LLM combinando todas las señales del lote."""
        blocks = []
        for s in self.signals:
            blocks.append(
                f"━━━ SEÑAL: {s.signal_type.upper()} ━━━\n"
                f"Proyecto: {s.project_name} (tipo={s.project_type})\n"
                f"{s.payload}"
            )
        return "\n\n".join(blocks)


# ── Agente de aprendizaje ────────────────────────────────────────────


class LearningAgent:
    """Extrae conocimiento a partir de señales del pipeline y lo almacena."""

    # Señales que se procesan juntas en una sola llamada al LLM
    MAX_SIGNALS_PER_BATCH = 5

    def __init__(self, settings: Settings, knowledge_memory: KnowledgeMemory) -> None:
        self.settings = settings
        self.knowledge = knowledge_memory
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = get_model(self.settings.llm_provider, self.settings.llm_model)
        return self._model

    # ── API compatible con la versión anterior ─────────────────────

    def learn_from_project(
        self,
        project_name: str,
        project_type: str,
        user_request: str,
        analysis_doc: str,
        design_doc: str,
        implementation_summary: str,
        validation_result: str,
        extra_context: Optional[str] = None,
    ) -> int:
        """Mantiene la API anterior. Internamente usa el sistema multi-señal."""
        batch = LearningBatch()

        # Señal de completion con el resumen completo
        completion_payload = f"""\
LO QUE PIDIÓ EL USUARIO:
{user_request[:500]}

REQUISITOS GENERADOS (resumen):
{analysis_doc[:1500]}

DISEÑO TÉCNICO (resumen):
{design_doc[:1500]}

IMPLEMENTACIÓN:
{implementation_summary[:800]}

VALIDACIÓN:
{validation_result[:500]}
"""
        if extra_context:
            completion_payload += f"\nCONTEXTO ADICIONAL:\n{extra_context[:300]}"

        batch.signals.append(LearningSignal(
            signal_type="completion",
            project_name=project_name,
            project_type=project_type,
            payload=completion_payload,
        ))
        return self._process_batch(batch)

    # ── Nuevas APIs para señales específicas ───────────────────────

    def learn_from_compiler_errors(
        self,
        project_name: str,
        project_type: str,
        errors_feedback: str,
    ) -> int:
        """Extrae conocimiento a partir de errores reales del code validator."""
        if not errors_feedback.strip():
            return 0
        batch = LearningBatch(signals=[LearningSignal(
            signal_type="compiler",
            project_name=project_name,
            project_type=project_type,
            payload=(
                "Errores del compilador/linter detectados durante la generación:\n\n"
                f"{errors_feedback[:2500]}\n\n"
                "Extrae insights tipo 'error_compilador' o 'anti_patron' que \
ayuden a evitar estos errores en futuros proyectos del mismo tipo."
            ),
        )])
        return self._process_batch(batch)

    def learn_from_gate_failures(
        self,
        project_name: str,
        project_type: str,
        gate_feedback: str,
    ) -> int:
        """Extrae conocimiento cuando quality gates detectan problemas."""
        if not gate_feedback.strip():
            return 0
        batch = LearningBatch(signals=[LearningSignal(
            signal_type="failure",
            project_name=project_name,
            project_type=project_type,
            payload=(
                "Quality gates que fallaron en este proyecto:\n\n"
                f"{gate_feedback[:2500]}\n\n"
                "Extrae insights 'falla_quality_gate' o 'anti_patron' que \
ayuden a evitar estas fallas en futuros proyectos."
            ),
        )])
        return self._process_batch(batch)

    def learn_from_validation_findings(
        self,
        project_name: str,
        project_type: str,
        validation_report: str,
    ) -> int:
        """Extrae conocimiento de hallazgos reales del agente de validación."""
        # Solo procesar si hay hallazgos críticos o altos
        if not any(k in validation_report.lower() for k in ["crítico", "alto", "severidad", "owasp"]):
            return 0
        batch = LearningBatch(signals=[LearningSignal(
            signal_type="validation",
            project_name=project_name,
            project_type=project_type,
            payload=(
                "Informe de validación del proyecto (fragmento relevante):\n\n"
                f"{validation_report[:3000]}\n\n"
                "Extrae insights 'hallazgo_validacion' o 'anti_patron' a partir "
                "de los problemas críticos/altos documentados."
            ),
        )])
        return self._process_batch(batch)

    def learn_from_user_preferences(
        self,
        user_conversation: str,
        project_name: str = "conversacion",
        project_type: str = "mixed",
    ) -> int:
        """Extrae preferencias explícitas del usuario durante el diálogo."""
        if len(user_conversation.strip()) < 100:
            return 0
        batch = LearningBatch(signals=[LearningSignal(
            signal_type="user_pref",
            project_name=project_name,
            project_type=project_type,
            payload=(
                "Conversación con el usuario durante el descubrimiento:\n\n"
                f"{user_conversation[:3000]}\n\n"
                "Extrae preferencias explícitas del usuario: "
                "categorías válidas son 'preferencia_usuario' o 'convencion_nombres'. "
                "Solo extrae cosas que el usuario DIJO explícitamente, no inferidas."
            ),
        )])
        return self._process_batch(batch)

    # ── Feedback loop para refuerzo/castigo ─────────────────────────

    def mark_used_insights_success(self, insight_ids: List[int]) -> None:
        """Refuerza los insights usados si el proyecto terminó bien."""
        self.knowledge.apply_feedback(insight_ids, positive=True)

    def mark_used_insights_failure(self, insight_ids: List[int]) -> None:
        """Penaliza los insights usados si el proyecto terminó con problemas."""
        self.knowledge.apply_feedback(insight_ids, positive=False)

    # ── Mantenimiento periódico ────────────────────────────────────

    def periodic_maintenance(
        self, apply_decay: bool = True, consolidate: bool = True
    ) -> dict:
        """Ejecuta mantenimiento: decay temporal + consolidación de clusters.

        Pensado para llamarse al inicio de cada sesión o cada N proyectos.

        Returns:
            Dict con métricas del mantenimiento realizado.
        """
        stats = {"decay_affected": 0, "consolidated": 0}
        try:
            if apply_decay:
                stats["decay_affected"] = self.knowledge.apply_temporal_decay()
            if consolidate:
                stats["consolidated"] = self.knowledge.consolidate_clusters()
        except Exception as e:
            logger.warning("Error en mantenimiento: %s", e)
        return stats

    # ── Motor interno de procesamiento ─────────────────────────────

    def _process_batch(self, batch: LearningBatch) -> int:
        """Procesa un lote de señales con una llamada al LLM."""
        if batch.is_empty() or not self.knowledge:
            return 0

        try:
            from agno.agent import Agent  # import tardío
            model = self._get_model()
            extractor = Agent(
                model=model,
                instructions=[_BASE_EXTRACTION_PROMPT],
                markdown=False,
            )
            prompt = (
                "Analiza la siguiente evidencia de un proyecto y extrae "
                "conocimiento reutilizable:\n\n"
                + batch.render_for_extraction()
            )
            result = extractor.run(prompt)
            if not result or not getattr(result, "content", None):
                return 0

            raw = result.content.strip()
            raw = self._strip_markdown_fence(raw)

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Intentar recuperar un JSON embebido
                match = re.search(r"\{.*\}", raw, re.DOTALL)
                if not match:
                    logger.warning("JSON no parseable del extractor de aprendizaje")
                    return 0
                data = json.loads(match.group(0))

            insights = data.get("insights", [])
            if not isinstance(insights, list):
                return 0

            saved = 0
            # Mapear la primera señal como contexto dominante (todas son del mismo proyecto)
            dominant = batch.signals[0]
            for item in insights:
                category = item.get("category", "patron_exitoso")
                if category not in KNOWLEDGE_CATEGORIES:
                    category = "patron_exitoso"
                title = str(item.get("title", "Sin título")).strip()[:80]
                insight_text = str(item.get("insight", "")).strip()[:300]
                if not title or not insight_text:
                    continue
                ok = self.knowledge.store_insight(
                    category=category,
                    title=title,
                    insight=insight_text,
                    context=f"Proyecto: {dominant.project_name} | Tipo: {dominant.project_type}",
                    project_type=item.get("project_type", dominant.project_type),
                    tags=item.get("tags") or [],
                    source_signal=dominant.signal_type,
                )
                if ok:
                    saved += 1

            logger.info(
                "Aprendizaje batch: %d insights de %d señales (%s)",
                saved, len(batch.signals), dominant.signal_type,
            )
            return saved
        except Exception as e:
            logger.error("Error en procesamiento de lote: %s", e)
            return 0

    @staticmethod
    def _strip_markdown_fence(raw: str) -> str:
        """Quita bloques de código markdown si el LLM los agregó."""
        if raw.startswith("```"):
            parts = raw.split("```")
            if len(parts) >= 2:
                block = parts[1]
                if block.startswith("json"):
                    block = block[4:]
                return block.strip()
        return raw
