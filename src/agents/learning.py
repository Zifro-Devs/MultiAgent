"""Agente de Aprendizaje Autónomo.

Se ejecuta automáticamente al terminar cada proyecto.
Analiza todo lo que pasó y extrae conocimiento útil para el futuro:
patrones, anti-patrones, preferencias, decisiones técnicas, etc.

La IA decide qué vale la pena recordar. No guarda chats, guarda sabiduría.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.config.settings import Settings, get_model
from src.storage.knowledge_memory import KnowledgeMemory, KNOWLEDGE_CATEGORIES

logger = logging.getLogger(__name__)

LEARNING_PROMPT = """\
Eres un sistema de aprendizaje autónomo. Tu único trabajo es analizar lo que ocurrió \
en un proyecto de desarrollo de software y extraer conocimiento útil y reutilizable.

NO eres un asistente. NO respondes al usuario. SOLO extraes conocimiento.

CATEGORÍAS DISPONIBLES:
- patron_exitoso: algo que funcionó bien y vale repetir en futuros proyectos
- anti_patron: algo que causó problemas, errores o ineficiencias
- preferencia_usuario: lo que los usuarios piden frecuentemente o valoran
- decision_tecnica: stack, librerías, arquitecturas que funcionaron bien
- solucion_problema: cómo se resolvió un problema técnico específico
- estructura_proyecto: cómo se organizó el código de forma exitosa
- integracion: APIs, servicios externos, integraciones que se implementaron
- error_comun: errores frecuentes y cómo evitarlos

REGLAS:
1. Extrae SOLO conocimiento concreto y accionable, no generalidades
2. Cada insight debe ser útil para un proyecto FUTURO similar
3. Sé específico: "usar JWT con refresh tokens para auth en APIs REST" es bueno, \
"usar autenticación" es inútil
4. Si no hay nada valioso que aprender, devuelve lista vacía
5. Máximo 10 insights por proyecto, solo los más valiosos
6. SIEMPRE responde con JSON válido, sin texto adicional

FORMATO DE RESPUESTA (JSON puro, sin markdown):
{
  "insights": [
    {
      "category": "patron_exitoso",
      "title": "Título corto (max 80 chars)",
      "insight": "Descripción concreta y accionable de qué aprender (max 300 chars)",
      "project_type": "web|api|mobile|cli|data|ml|desktop",
      "tags": ["tag1", "tag2"]
    }
  ]
}
"""


class LearningAgent:
    """Agente que aprende de cada proyecto completado."""

    def __init__(self, settings: Settings, knowledge_memory: KnowledgeMemory):
        self.settings = settings
        self.knowledge = knowledge_memory
        self._model = None

    def _get_model(self):
        if self._model is None:
            self._model = get_model(self.settings.llm_provider, self.settings.llm_model)
        return self._model

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
        """Analiza un proyecto completado y guarda el conocimiento extraído.

        Args:
            project_name: Nombre del proyecto
            project_type: Tipo (web, api, mobile, etc.)
            user_request: Qué pidió el usuario originalmente
            analysis_doc: Documento de requisitos generado
            design_doc: Documento de diseño generado
            implementation_summary: Resumen de archivos/código generado
            validation_result: Resultado de la validación
            extra_context: Cualquier info adicional relevante

        Returns:
            Número de insights guardados
        """
        if not self.knowledge:
            return 0

        # Construir el contexto completo para que la IA analice
        analysis_input = f"""
PROYECTO: {project_name}
TIPO: {project_type}

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
            analysis_input += f"\nCONTEXTO ADICIONAL:\n{extra_context[:300]}"

        try:
            model = self._get_model()

            # Llamada directa al LLM
            from agno.agent import Agent
            extractor = Agent(
                model=model,
                instructions=[LEARNING_PROMPT],
                markdown=False,
            )

            result = extractor.run(
                f"Analiza este proyecto y extrae conocimiento útil:\n\n{analysis_input}"
            )

            if not result or not result.content:
                logger.warning("El agente de aprendizaje no devolvió contenido")
                return 0

            # Parsear JSON — limpiar posible markdown
            raw = result.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            insights = data.get("insights", [])

            saved = 0
            for item in insights:
                category = item.get("category", "patron_exitoso")
                if category not in KNOWLEDGE_CATEGORIES:
                    category = "patron_exitoso"

                ok = self.knowledge.store_insight(
                    category=category,
                    title=item.get("title", "Sin título")[:80],
                    insight=item.get("insight", "")[:300],
                    context=f"Proyecto: {project_name} | Tipo: {project_type}",
                    project_type=item.get("project_type", project_type),
                    tags=item.get("tags", []),
                )
                if ok:
                    saved += 1

            logger.info(f"Aprendizaje completado: {saved} insights guardados de '{project_name}'")
            return saved

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON del agente de aprendizaje: {e}")
            return 0
        except Exception as e:
            logger.error(f"Error en agente de aprendizaje: {e}")
            return 0
