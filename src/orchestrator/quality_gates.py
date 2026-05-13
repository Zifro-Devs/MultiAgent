"""Quality gates entre fases del pipeline.

Cada gate valida que la salida de una fase cumple los requisitos mínimos
antes de pasar a la siguiente. Si falla, devuelve una lista de problemas
concretos que pueden usarse para pedir corrección al agente.

Los gates NO ejecutan lógica de negocio ni generan contenido — solo
verifican estructura y completitud mediante reglas declarativas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


# ── Tipos ────────────────────────────────────────────────────────────


@dataclass
class GateResult:
    """Resultado de pasar un quality gate."""

    passed: bool
    phase: str
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def render_feedback(self) -> str:
        """Construye el feedback formateado para re-pedir al agente."""
        lines = [f"La salida de la fase '{self.phase}' no cumple los requisitos mínimos."]
        if self.issues:
            lines.append("\nPROBLEMAS QUE DEBES CORREGIR:")
            for i, problem in enumerate(self.issues, 1):
                lines.append(f"  {i}. {problem}")
        if self.warnings:
            lines.append("\nADVERTENCIAS (no bloquean, pero considéralas):")
            for w in self.warnings:
                lines.append(f"  · {w}")
        lines.append("\nRegenera la salida corrigiendo estos puntos. Mantén lo que ya estaba correcto.")
        return "\n".join(lines)


# ── Gate: Análisis ──────────────────────────────────────────────────


def gate_analysis(doc: str) -> GateResult:
    issues: List[str] = []
    warnings: List[str] = []

    if len(doc) < 1500:
        issues.append(
            "El documento de análisis es demasiado corto (<1500 caracteres). "
            "Debe contener versión ejecutiva + IEEE 830 completa."
        )

    # Secciones obligatorias
    required_headers = [
        (r"RESUMEN", "Falta sección de resumen ejecutivo"),
        (r"PERSONA|Personas|PARTE A", "Falta la sección de personas / parte ejecutiva"),
        (r"Requisitos funcionales|RF-001", "Falta la sección de Requisitos Funcionales"),
        (r"Requisitos no funcionales|RNF-", "Falta la sección de Requisitos No Funcionales"),
        (r"Historias de usuario|HU-001", "Falta la sección de Historias de Usuario"),
        (r"Modelo de datos|Entidades", "Falta el modelo de datos conceptual"),
    ]
    for pattern, msg in required_headers:
        if not re.search(pattern, doc, re.IGNORECASE):
            issues.append(msg)

    # Cantidad mínima de requisitos
    rf_count = len(re.findall(r"RF-\d+", doc))
    rnf_count = len(re.findall(r"RNF-[A-Z]?\d+", doc))
    hu_count = len(re.findall(r"HU-\d+", doc))

    if rf_count < 3:
        issues.append(f"Se detectaron solo {rf_count} requisitos funcionales. Mínimo esperado: 3")
    if rnf_count < 3:
        issues.append(f"Se detectaron solo {rnf_count} RNF. Mínimo esperado: 3")
    if hu_count < 2:
        warnings.append(f"Solo {hu_count} historias de usuario. Recomendado: 2 o más")

    # Palabras prohibidas (ambigüedad)
    ambiguous_words = ["rápido", "fácil", "intuitivo", "amigable", "moderno"]
    vague_hits = [w for w in ambiguous_words if re.search(rf"\b{w}\b", doc, re.IGNORECASE)]
    if len(vague_hits) >= 3:
        warnings.append(
            f"Se detectaron términos vagos sin métrica concreta: {', '.join(vague_hits)}. "
            "Considera reemplazarlos por criterios medibles."
        )

    # Criterios de aceptación
    acceptance = re.findall(r"(?:Given|Dado|Criterios de aceptación|cuando.*entonces)", doc, re.IGNORECASE)
    if len(acceptance) < 3:
        issues.append(
            "Pocos criterios de aceptación detectados. Cada RF principal debe tener "
            "criterios Given/When/Then testables."
        )

    return GateResult(passed=len(issues) == 0, phase="Análisis", issues=issues, warnings=warnings)


# ── Gate: Diseño ─────────────────────────────────────────────────────


def gate_design(doc: str) -> GateResult:
    issues: List[str] = []
    warnings: List[str] = []

    if len(doc) < 2500:
        issues.append("Documento de diseño demasiado corto (<2500 chars). Debe ser exhaustivo.")

    required_sections = [
        (r"Visi[oó]n General|Visi[oó]n general", "Falta sección de Visión General"),
        (r"Estilo arquitect|Patr[oó]n", "Falta sección de estilo arquitectónico"),
        (r"Componentes|##\s*3", "Falta descripción de componentes"),
        (r"Modelo de datos|Entidades|erDiagram", "Falta el modelo de datos con DDL"),
        (r"Contratos? de API|Endpoints|API", "Falta sección de contratos de API"),
        (r"Stack tecnol[oó]gico", "Falta sección de stack tecnológico"),
        (r"Seguridad", "Falta sección de arquitectura de seguridad"),
        (r"ADR-?\s*001|Decisiones arquitect", "Faltan ADRs (Architecture Decision Records)"),
        (r"CONTRATO DE IMPLEMENTACI|PROJECT_TYPE", "Falta el CONTRATO DE IMPLEMENTACIÓN (sección 11)"),
    ]
    for pattern, msg in required_sections:
        if not re.search(pattern, doc, re.IGNORECASE):
            issues.append(msg)

    # Campos mínimos del contrato de implementación
    if re.search(r"CONTRATO DE IMPLEMENTACI", doc, re.IGNORECASE):
        contract_fields = ["PROJECT_TYPE", "LANGUAGE"]
        for field_name in contract_fields:
            if not re.search(rf"{field_name}\s*:", doc):
                issues.append(f"Campo requerido '{field_name}' ausente en el contrato de implementación")

    # Diagramas Mermaid
    mermaid_blocks = re.findall(r"```mermaid", doc)
    if len(mermaid_blocks) == 0:
        warnings.append("No se detectaron diagramas Mermaid. Se recomienda al menos uno.")

    # ADRs
    adr_count = len(re.findall(r"ADR-\d+", doc))
    if adr_count < 3:
        warnings.append(f"Solo {adr_count} ADRs. Recomendado: 5 o más para decisiones significativas.")

    return GateResult(passed=len(issues) == 0, phase="Diseño", issues=issues, warnings=warnings)


# ── Gate: Implementación ────────────────────────────────────────────


# Archivos comúnmente esperados según el stack
_CORE_FILE_HINTS = {
    "nodejs": ["package.json", ".env.example", "README.md"],
    "python": ["requirements.txt", ".env.example", "README.md"],
    "python-poetry": ["pyproject.toml", ".env.example", "README.md"],
    "go": ["go.mod", ".env.example", "README.md"],
    "rust": ["Cargo.toml", ".env.example", "README.md"],
}


def gate_implementation(artifacts_dir: Path, profile: Optional[object] = None) -> GateResult:
    """Valida que la implementación generó un proyecto coherente."""
    issues: List[str] = []
    warnings: List[str] = []

    if not artifacts_dir.exists():
        return GateResult(
            passed=False,
            phase="Implementación",
            issues=[f"El directorio de artefactos '{artifacts_dir}' no existe"],
        )

    files = [f for f in artifacts_dir.rglob("*") if f.is_file()]
    rel_paths = {str(f.relative_to(artifacts_dir)).replace("\\", "/") for f in files}

    if len(files) < 5:
        issues.append(
            f"Solo se generaron {len(files)} archivos. Un proyecto real requiere "
            f"al menos una decena de archivos."
        )

    # README + .env.example + algo de dependencias
    has_readme = any("README" in p.upper() for p in rel_paths)
    has_env_example = any(p.endswith(".env.example") for p in rel_paths)
    has_gitignore = any(p.endswith(".gitignore") for p in rel_paths)
    has_deps = any(
        p.endswith(x)
        for p in rel_paths
        for x in ("package.json", "requirements.txt", "pyproject.toml", "go.mod", "Cargo.toml")
    )

    if not has_readme:
        issues.append("Falta archivo README.md en la raíz del proyecto")
    if not has_deps:
        issues.append(
            "Falta archivo de dependencias (package.json, requirements.txt, pyproject.toml, "
            "go.mod o Cargo.toml)"
        )
    if not has_env_example:
        warnings.append("No se encontró .env.example — recomendado para documentar configuración")
    if not has_gitignore:
        warnings.append("No se encontró .gitignore — recomendado para evitar commits de secrets")

    # Detectar anti-patrones en contenido
    antipatterns = {
        r"TODO:.*implementar": "Se detectaron TODOs de implementación pendientes — el código debe estar completo",
        r"placeholder|PLACEHOLDER": "Se detectaron placeholders en el código",
        r"# aqu[ií] va la l[oó]gica|// aqu[ií] va la l[oó]gica": "Se detectaron marcadores de 'aquí va la lógica'",
    }
    hits: List[str] = []
    for f in files:
        if f.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java"}:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern, msg in antipatterns.items():
            if re.search(pattern, content):
                rel = str(f.relative_to(artifacts_dir)).replace("\\", "/")
                hits.append(f"{rel}: {msg}")
                break  # un hit por archivo basta

    if hits:
        issues.extend(hits[:10])  # máximo 10 para no saturar
        if len(hits) > 10:
            issues.append(f"... y {len(hits) - 10} archivos más con anti-patrones similares")

    # Detectar secretos obvios
    secret_patterns = [
        (r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{8,}['\"]",
         "Posible credencial hardcodeada"),
        (r"sk-[a-zA-Z0-9]{20,}", "Posible API key de OpenAI/OpenRouter hardcodeada"),
    ]
    for f in files:
        if f.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".env"}:
            continue
        if f.name == ".env.example":
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern, msg in secret_patterns:
            m = re.search(pattern, content)
            if m:
                rel = str(f.relative_to(artifacts_dir)).replace("\\", "/")
                issues.append(f"{rel}: {msg} — '{m.group(0)[:40]}...'")

    return GateResult(
        passed=len(issues) == 0,
        phase="Implementación",
        issues=issues,
        warnings=warnings,
    )


# ── Gate: Testing ────────────────────────────────────────────────────


def gate_testing(artifacts_dir: Path) -> GateResult:
    """Valida que existan tests en una estructura razonable."""
    issues: List[str] = []
    warnings: List[str] = []

    if not artifacts_dir.exists():
        return GateResult(
            passed=False,
            phase="Testing",
            issues=[f"El directorio de artefactos '{artifacts_dir}' no existe"],
        )

    files = list(artifacts_dir.rglob("*"))

    # Buscar carpetas/archivos de test
    test_patterns = [
        r"tests?/",
        r"__tests__/",
        r"test_[a-z0-9_]+\.py",
        r"[a-z0-9_.-]+\.test\.[jt]sx?",
        r"[a-z0-9_.-]+\.spec\.[jt]sx?",
        r"_test\.go",
    ]

    test_files = []
    for f in files:
        if not f.is_file():
            continue
        rel = str(f.relative_to(artifacts_dir)).replace("\\", "/")
        for pattern in test_patterns:
            if re.search(pattern, rel):
                test_files.append(rel)
                break

    if not test_files:
        issues.append(
            "No se detectaron archivos de test. El agente de testing debe generar "
            "al menos una suite mínima."
        )
    elif len(test_files) < 3:
        warnings.append(
            f"Solo {len(test_files)} archivos de test. Se recomienda mayor cobertura."
        )

    return GateResult(
        passed=len(issues) == 0,
        phase="Testing",
        issues=issues,
        warnings=warnings,
    )
