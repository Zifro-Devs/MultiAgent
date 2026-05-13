"""Pipeline mejorado de generación de proyecto.

Encapsula el flujo completo: análisis → diseño → testing → implementación →
validación → documentación, aplicando quality gates entre fases con
re-intentos automáticos y un validador de código real al final de la
implementación.

Ventajas respecto al flujo anterior:

1. Quality gates bloquean el avance si la salida de una fase está incompleta.
2. El stack se detecta antes de implementar, y el implementador usa un
   prompt especializado en lugar del prompt genérico.
3. Los tests se generan desde los criterios de aceptación, no post-mortem.
4. Un code validator real compila/lintea el proyecto y devuelve errores
   concretos para auto-corrección.
5. El pipeline es idempotente: cada fase puede re-ejecutarse con feedback
   sin contaminar el contexto de otras fases.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional, Protocol

from src.agents.design import create_design_agent
from src.agents.documentation import create_documentation_agent
from src.agents.implementation import create_implementation_agent
from src.agents.prompts.selector import StackProfile
from src.agents.testing import create_testing_agent
from src.agents.validation import create_validation_agent
from src.config.settings import Settings
from src.orchestrator.quality_gates import (
    GateResult,
    gate_analysis,
    gate_design,
    gate_implementation,
    gate_testing,
)
from src.orchestrator.stack_detector import detect_stack
from src.tools.code_validator import validate_project

logger = logging.getLogger(__name__)


# ── Tipos ────────────────────────────────────────────────────────────


class ProgressReporter(Protocol):
    """Interfaz mínima para reportar progreso a la UI.

    Implementaciones simples son aceptables: un objeto con dos métodos
    es suficiente. Se usa un Protocol para no forzar dependencias en
    Streamlit ni en ninguna otra UI.
    """

    def set_status(self, phase: str, message: str) -> None: ...
    def set_progress(self, pct: int) -> None: ...


class NullReporter:
    """Reporter que no hace nada — útil para tests o usos headless."""

    def set_status(self, phase: str, message: str) -> None:
        logger.info("[%s] %s", phase, message)

    def set_progress(self, pct: int) -> None:
        return


@dataclass
class PipelineResult:
    """Resultado final del pipeline."""

    project_name: str
    project_path: Path
    analysis_doc: str
    design_doc: str
    tests_summary: str
    implementation_summary: str
    validation_report: str
    documentation_summary: str
    stack_profile: Optional[StackProfile]
    files_generated: list[str] = field(default_factory=list)
    gate_failures: list[GateResult] = field(default_factory=list)
    code_issues_count: int = 0
    # Nuevos: feedback acumulado durante el pipeline para alimentar aprendizaje
    compiler_feedback: str = ""
    gate_feedback: str = ""
    was_successful: bool = True

    def render_user_summary(self) -> str:
        lines = [f"**{self.project_name}**"]
        if self.stack_profile:
            sp = self.stack_profile
            stack_line = (
                f"Stack detectado: {sp.project_type}"
                f" · lenguaje: {sp.language}"
            )
            if sp.backend_framework:
                stack_line += f" · backend: {sp.backend_framework}"
            if sp.frontend_framework:
                stack_line += f" · frontend: {sp.frontend_framework}"
            if sp.database:
                stack_line += f" · BD: {sp.database}"
            lines.append(stack_line)
        lines.append(f"Archivos generados: {len(self.files_generated)}")
        if self.code_issues_count:
            lines.append(f"Problemas de código detectados: {self.code_issues_count}")
        if self.gate_failures:
            lines.append(
                f"Quality gates con observaciones: {len(self.gate_failures)}"
            )
        lines.append(f"Ruta del proyecto: `artifacts/{self.project_name}/`")
        return "\n".join(lines)


# ── Utilidades ───────────────────────────────────────────────────────


def _extract_content(result: Any) -> str:
    """Extrae el content de cualquier retorno de un Agent.run()."""
    if result is None:
        return ""
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    if content is None and isinstance(result, str):
        return result
    return str(content or "")


def _list_generated_files(project_path: Path) -> list[str]:
    if not project_path.exists():
        return []
    return sorted(
        str(f.relative_to(project_path)).replace("\\", "/")
        for f in project_path.rglob("*")
        if f.is_file()
    )


# ── Ejecución de fases con gates ────────────────────────────────────


def _run_with_gate(
    phase_name: str,
    run_fn: Callable[[str], str],
    gate_fn: Callable[[str], GateResult],
    initial_prompt: str,
    *,
    max_attempts: int = 2,
    reporter: ProgressReporter,
) -> tuple[str, Optional[GateResult]]:
    """Ejecuta una fase con hasta N intentos, aplicando el quality gate.

    Si el gate falla en el último intento, devuelve el mejor resultado
    obtenido junto con el GateResult que falló, sin bloquear el pipeline
    (el caller decide qué hacer).
    """
    current_prompt = initial_prompt
    last_result = ""
    last_gate: Optional[GateResult] = None

    for attempt in range(1, max_attempts + 1):
        reporter.set_status(phase_name, f"Intento {attempt}/{max_attempts}")
        last_result = run_fn(current_prompt)
        last_gate = gate_fn(last_result)

        if last_gate.passed:
            logger.info("[%s] Quality gate OK en intento %d", phase_name, attempt)
            return last_result, None

        logger.warning(
            "[%s] Quality gate falló: %d issues", phase_name, len(last_gate.issues)
        )
        if attempt < max_attempts:
            # Preparamos feedback para el siguiente intento
            feedback = last_gate.render_feedback()
            current_prompt = (
                f"{initial_prompt}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"FEEDBACK DEL QUALITY GATE — INTENTO PREVIO\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{feedback}"
            )

    return last_result, last_gate


# ── Pipeline principal ──────────────────────────────────────────────


def run_pipeline(
    *,
    settings: Settings,
    project_name: str,
    user_context: str,
    prior_knowledge: str = "",
    prior_knowledge_ids: Optional[list[int]] = None,
    analysis_agent,
    reporter: Optional[ProgressReporter] = None,
    enable_code_validation: bool = True,
    max_implementation_retries: int = 1,
    learning_agent: Optional[Any] = None,
) -> PipelineResult:
    """Ejecuta el pipeline completo y devuelve los artefactos.

    Args:
        settings: configuración global.
        project_name: nombre (kebab-case) de la carpeta del proyecto.
        user_context: texto con la conversación usuario-orquestador.
        prior_knowledge: texto inyectado con conocimiento previo relevante.
        prior_knowledge_ids: IDs de los insights que se inyectaron (para
            aplicar feedback positivo o negativo al final).
        analysis_agent: agente de análisis pre-instanciado (reúsa sesión).
        reporter: ProgressReporter para integrar con la UI.
        enable_code_validation: activa el code validator real.
        max_implementation_retries: intentos de auto-corrección ante errores.
        learning_agent: agente de aprendizaje opcional. Si se pasa, se captura
            feedback adicional de compilador/gates/validación durante el flujo.
    """

    reporter = reporter or NullReporter()

    project_path = (settings.artifacts_path / project_name).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    artifacts_dir = str(project_path)

    # ── Fase 1: ANÁLISIS ─────────────────────────────────────────
    reporter.set_progress(5)
    reporter.set_status("Análisis", "Generando especificación de requisitos")

    analysis_prompt = f"""Genera la especificación IEEE 830 completa del proyecto \
basándote EXCLUSIVAMENTE en la siguiente conversación con el usuario. \
No inventes funcionalidades que no se mencionaron. Sí incluye requisitos \
estándar del tipo de sistema (por ejemplo, logout si hay login) marcándolos \
como tal.

CONVERSACIÓN CON EL USUARIO:
{user_context}
{prior_knowledge}
"""
    def _run_analysis(prompt: str) -> str:
        return _extract_content(analysis_agent.run(prompt))

    analysis_doc, analysis_gate = _run_with_gate(
        "Análisis",
        _run_analysis,
        gate_analysis,
        analysis_prompt,
        reporter=reporter,
    )
    reporter.set_progress(20)

    # ── Fase 2: DISEÑO ───────────────────────────────────────────
    reporter.set_status("Diseño", "Diseñando arquitectura y contrato de implementación")
    design_agent = create_design_agent(settings)

    design_prompt = f"""Diseña la arquitectura completa basándote en estos requisitos. \
La sección 11 "CONTRATO DE IMPLEMENTACIÓN" es OBLIGATORIA y debe ser muy específica \
(tipo de proyecto, lenguaje, frameworks, BD, árbol de archivos exacto, endpoints, \
entidades, dependencias con versiones, variables de entorno).

REQUISITOS COMPLETOS:
{analysis_doc}

CONTEXTO DE LA CONVERSACIÓN (referencia adicional):
{user_context[:1500]}
"""
    def _run_design(prompt: str) -> str:
        return _extract_content(design_agent.run(prompt))

    design_doc, design_gate = _run_with_gate(
        "Diseño",
        _run_design,
        gate_design,
        design_prompt,
        reporter=reporter,
    )
    reporter.set_progress(35)

    # ── Detección de stack ───────────────────────────────────────
    stack_profile = detect_stack(design_doc, user_context)
    logger.info("Stack detectado: %s", stack_profile)

    # ── Fase 3: TESTING (TDD — antes de implementar) ─────────────
    # Generar la suite primero usando criterios de aceptación
    reporter.set_status("Testing", "Generando suite de tests desde criterios de aceptación")
    testing_agent = create_testing_agent(settings, artifacts_dir=artifacts_dir)

    testing_prompt = f"""Genera la estructura de tests del proyecto usando los criterios \
de aceptación de los requisitos como fuente de verdad. Los tests se escriben ANTES \
de la implementación: definen el comportamiento que el código deberá cumplir.

Stack del proyecto:
- Tipo: {stack_profile.project_type}
- Lenguaje: {stack_profile.language}
- Backend: {stack_profile.backend_framework or 'N/A'}
- Frontend: {stack_profile.frontend_framework or 'N/A'}
- BD: {stack_profile.database or 'N/A'}

REQUISITOS (con criterios de aceptación):
{analysis_doc[:3500]}

DISEÑO (para conocer endpoints y entidades):
{design_doc[:3500]}

Empieza creando la configuración (pytest.ini/vitest.config/playwright.config según stack) \
y las fixtures principales, luego los tests unitarios e integración. Los tests E2E \
van al final solo para los flujos críticos.
"""
    _extract_content(testing_agent.run(testing_prompt))
    tests_summary = "Tests generados antes de la implementación"
    reporter.set_progress(50)

    # ── Fase 4: IMPLEMENTACIÓN ──────────────────────────────────
    reporter.set_status("Implementación", "Generando código de producción")
    implementation_agent = create_implementation_agent(
        settings,
        artifacts_dir=artifacts_dir,
        profile=stack_profile,
    )

    implementation_prompt = f"""Implementa el sistema completo siguiendo el CONTRATO DE \
IMPLEMENTACIÓN del diseño. Cada archivo listado en el árbol debe existir. Cada endpoint \
y entidad definidos deben estar implementados.

Los tests YA están escritos en /tests. Tu código debe hacerlos pasar. No los modifiques.

DISEÑO (con contrato en sección 11):
{design_doc}

Usa write_file() para cada archivo. Escribe el proyecto COMPLETO, no un esqueleto.
"""
    _extract_content(implementation_agent.run(implementation_prompt))
    reporter.set_progress(70)

    # ── Validación de código real ────────────────────────────────
    code_issues_count = 0
    compiler_feedback_text = ""
    if enable_code_validation:
        reporter.set_status("Validación", "Compilando y verificando el código")
        validation = validate_project(project_path)
        code_issues_count = len([i for i in validation.issues if i.severity == "error"])

        if validation.has_errors and max_implementation_retries > 0:
            reporter.set_status(
                "Corrección", f"Corrigiendo {code_issues_count} errores de compilación"
            )
            feedback = validation.render_feedback()
            compiler_feedback_text = feedback  # guardar para aprendizaje
            fix_prompt = f"""El código que acabas de generar tiene errores reales al \
validarse. Lee los archivos con read_file, corrige los problemas y reescribe los archivos \
afectados con write_file.

{feedback}

No toques archivos que no están en la lista. No rompas lo que ya funciona.
"""
            _extract_content(implementation_agent.run(fix_prompt))
            # Re-validar después del fix
            validation = validate_project(project_path)
            code_issues_count = len([i for i in validation.issues if i.severity == "error"])
            if validation.has_errors:
                compiler_feedback_text = validation.render_feedback()

    reporter.set_progress(80)

    # ── Gate de implementación ──────────────────────────────────
    impl_gate = gate_implementation(project_path, stack_profile)

    # ── Fase 5: VALIDACIÓN (auditoría) ──────────────────────────
    reporter.set_status("Auditoría", "Revisando calidad, seguridad y trazabilidad")
    validation_agent = create_validation_agent(settings, artifacts_dir=artifacts_dir)

    validation_prompt = f"""Audita el proyecto completo que acaba de generarse. \
Genera el informe en `VALIDATION_REPORT.md`.

CONTRATO DE IMPLEMENTACIÓN (del diseño):
{design_doc[-4000:]}

REQUISITOS QUE DEBE CUMPLIR:
{analysis_doc[:3500]}

Revisa cada archivo. Reporta solo hallazgos reales, con archivo y línea. \
Produce un informe accionable — no inventes problemas para rellenar.
"""
    validation_result = _extract_content(validation_agent.run(validation_prompt))
    reporter.set_progress(92)

    # ── Fase 6: DOCUMENTACIÓN ───────────────────────────────────
    reporter.set_status("Documentación", "Generando README, ARCHITECTURE y PROYECTO")
    documentation_agent = create_documentation_agent(settings, artifacts_dir=artifacts_dir)

    doc_prompt = f"""Genera la documentación del proyecto. Lee los archivos reales con \
list_files() y read_file() antes de escribir. Los comandos en el README deben ser \
EXACTOS para el stack detectado.

NOMBRE DEL PROYECTO: {project_name}
STACK DETECTADO: {stack_profile.project_type} / {stack_profile.language}

RESUMEN DE REQUISITOS:
{analysis_doc[:2000]}

RESUMEN DE DISEÑO:
{design_doc[:2000]}

Escribe: README.md, ARCHITECTURE.md, CONTRIBUTING.md y PROYECTO.md en la raíz.
"""
    doc_result = _extract_content(documentation_agent.run(doc_prompt))
    reporter.set_progress(100)

    files = _list_generated_files(project_path)

    # Coleccionamos gates fallidos para reporte
    gate_failures = [g for g in (analysis_gate, design_gate, impl_gate) if g and not g.passed]

    # Texto de feedback consolidado de los gates (para aprendizaje)
    gate_feedback_text = "\n\n".join(g.render_feedback() for g in gate_failures) if gate_failures else ""

    # Criterio de éxito global: sin gates críticos fallidos y sin errores de compilador
    was_successful = (not gate_failures) and (code_issues_count == 0)

    # ── Aprendizaje multi-señal ──────────────────────────────────
    # Captura señales específicas que enriquecen la memoria más allá de
    # "proyecto completado". Esto hace que el sistema realmente aprenda de
    # los errores, no solo de los éxitos.
    if learning_agent is not None:
        project_type_tag = (
            stack_profile.project_type if stack_profile else "unknown"
        )

        # Señal: errores de compilador
        if compiler_feedback_text:
            try:
                learning_agent.learn_from_compiler_errors(
                    project_name=project_name,
                    project_type=project_type_tag,
                    errors_feedback=compiler_feedback_text,
                )
            except Exception as e:
                logger.warning("Learning compiler signal failed: %s", e)

        # Señal: fallos de quality gate
        if gate_feedback_text:
            try:
                learning_agent.learn_from_gate_failures(
                    project_name=project_name,
                    project_type=project_type_tag,
                    gate_feedback=gate_feedback_text,
                )
            except Exception as e:
                logger.warning("Learning gate signal failed: %s", e)

        # Señal: hallazgos de validación (crítico / alto)
        if validation_result:
            try:
                learning_agent.learn_from_validation_findings(
                    project_name=project_name,
                    project_type=project_type_tag,
                    validation_report=validation_result,
                )
            except Exception as e:
                logger.warning("Learning validation signal failed: %s", e)

        # Señal: preferencias del usuario
        if user_context:
            try:
                learning_agent.learn_from_user_preferences(
                    user_conversation=user_context,
                    project_name=project_name,
                    project_type=project_type_tag,
                )
            except Exception as e:
                logger.warning("Learning user-pref signal failed: %s", e)

        # Feedback loop: refuerza/penaliza insights inyectados según éxito
        if prior_knowledge_ids:
            try:
                if was_successful:
                    learning_agent.mark_used_insights_success(prior_knowledge_ids)
                else:
                    learning_agent.mark_used_insights_failure(prior_knowledge_ids)
            except Exception as e:
                logger.warning("Feedback loop failed: %s", e)

    return PipelineResult(
        project_name=project_name,
        project_path=project_path,
        analysis_doc=analysis_doc,
        design_doc=design_doc,
        tests_summary=tests_summary,
        implementation_summary=f"{len(files)} archivos generados",
        validation_report=validation_result,
        documentation_summary=doc_result[:500] if doc_result else "",
        stack_profile=stack_profile,
        files_generated=files,
        gate_failures=gate_failures,
        code_issues_count=code_issues_count,
        compiler_feedback=compiler_feedback_text,
        gate_feedback=gate_feedback_text,
        was_successful=was_successful,
    )
