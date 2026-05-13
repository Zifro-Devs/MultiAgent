"""Validador real de código generado.

Detecta el stack del proyecto y ejecuta las herramientas apropiadas para
validar que el código compila, tiene tipos correctos y pasa linting básico.
Devuelve errores estructurados que pueden enviarse de vuelta al agente
implementador para auto-corrección.

Diseño:
- Las validaciones son opt-in: solo se ejecutan las herramientas que están
  instaladas en el sistema. No bloquea si faltan.
- Cada validación corre con timeout corto para no colgar el pipeline.
- Los errores se limitan en cantidad para mantener el feedback accionable.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """Un problema detectado por un validador."""

    tool: str
    file: str
    line: Optional[int]
    severity: str  # "error" | "warning"
    message: str


@dataclass
class ValidationResult:
    """Resultado de validar todo el proyecto."""

    issues: List[ValidationIssue] = field(default_factory=list)
    tools_run: List[str] = field(default_factory=list)
    tools_skipped: List[str] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def render_feedback(self, max_issues: int = 25) -> str:
        """Formatea el resultado como feedback accionable para el agente."""
        if not self.issues:
            return ""

        by_severity = {"error": [], "warning": []}
        for issue in self.issues:
            by_severity[issue.severity].append(issue)

        lines = ["Se detectaron problemas reales en el código generado al validarlo."]

        if by_severity["error"]:
            lines.append(f"\nERRORES ({len(by_severity['error'])}) — BLOQUEANTES:")
            for issue in by_severity["error"][:max_issues]:
                loc = f"{issue.file}:{issue.line}" if issue.line else issue.file
                lines.append(f"  [{issue.tool}] {loc} → {issue.message}")

        if by_severity["warning"]:
            remaining = max_issues - len(by_severity["error"])
            if remaining > 0:
                lines.append(f"\nADVERTENCIAS ({len(by_severity['warning'])}):")
                for issue in by_severity["warning"][:remaining]:
                    loc = f"{issue.file}:{issue.line}" if issue.line else issue.file
                    lines.append(f"  [{issue.tool}] {loc} → {issue.message}")

        lines.append(
            "\nCORRIGE cada error reescribiendo el archivo afectado completo con write_file(). "
            "Mantén lo que ya estaba correcto. No dejes ningún error bloqueante."
        )
        return "\n".join(lines)


# ── Detección de stack ──────────────────────────────────────────────


def _detect_language(root: Path) -> Tuple[str, List[Path]]:
    """Detecta el lenguaje predominante y devuelve archivos del mismo."""
    counters = {
        "python": list(root.rglob("*.py")),
        "typescript": list(root.rglob("*.ts")) + list(root.rglob("*.tsx")),
        "javascript": list(root.rglob("*.js")) + list(root.rglob("*.jsx")),
        "go": list(root.rglob("*.go")),
        "rust": list(root.rglob("*.rs")),
    }
    # Excluir node_modules / venv / dist / build
    def _filter(paths: List[Path]) -> List[Path]:
        excluded = {"node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next"}
        return [p for p in paths if not set(p.parts).intersection(excluded)]

    counters = {k: _filter(v) for k, v in counters.items()}
    if not any(counters.values()):
        return "unknown", []

    language = max(counters, key=lambda k: len(counters[k]))
    return language, counters[language]


def _has_command(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(cmd: List[str], cwd: Path, timeout: int = 60) -> Tuple[int, str, str]:
    """Ejecuta un comando con timeout y captura stdout/stderr."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 124, "", f"Timeout after {timeout}s: {' '.join(cmd)}"
    except FileNotFoundError as e:
        return 127, "", str(e)
    except Exception as e:
        logger.warning("Command %s failed: %s", cmd, e)
        return 1, "", str(e)


# ── Validadores por lenguaje ────────────────────────────────────────


def _validate_python(root: Path, files: List[Path], result: ValidationResult) -> None:
    """Valida código Python con py_compile + opcionalmente ruff y mypy."""
    # py_compile — siempre disponible
    if _has_command("python"):
        result.tools_run.append("py_compile")
        for f in files[:50]:  # limitar para no explotar
            rel = str(f.relative_to(root)).replace("\\", "/")
            code, _, err = _run(["python", "-m", "py_compile", str(f)], root, timeout=15)
            if code != 0:
                # parse: "  File "...", line N"
                m = re.search(r"line (\d+)", err)
                line = int(m.group(1)) if m else None
                msg = err.strip().split("\n")[-1][:200]
                result.issues.append(ValidationIssue(
                    tool="py_compile", file=rel, line=line, severity="error", message=msg,
                ))

    # ruff — solo si está instalado
    if _has_command("ruff"):
        result.tools_run.append("ruff")
        code, stdout, _ = _run(
            ["ruff", "check", ".", "--output-format=json", "--no-fix"],
            root,
            timeout=30,
        )
        if stdout.strip():
            try:
                items = json.loads(stdout)
                for item in items[:30]:
                    result.issues.append(ValidationIssue(
                        tool="ruff",
                        file=item.get("filename", "").replace(str(root), "").lstrip("/\\"),
                        line=item.get("location", {}).get("row"),
                        severity="warning",
                        message=f"{item.get('code', '')}: {item.get('message', '')}"[:200],
                    ))
            except json.JSONDecodeError:
                pass
    else:
        result.tools_skipped.append("ruff (not installed)")


def _validate_typescript(root: Path, files: List[Path], result: ValidationResult) -> None:
    """Valida TS/JS si hay tsc o node+esbuild disponibles."""
    # Si hay package.json, intentar usar npx tsc --noEmit
    has_package_json = (root / "package.json").exists()

    if not has_package_json:
        result.tools_skipped.append("tsc (no package.json)")
        return

    # Verificar que las dependencias estén instaladas (o intentar instalarlas)
    node_modules = root / "node_modules"
    if not node_modules.exists():
        if _has_command("npm"):
            logger.info("Installing dependencies to enable TS validation...")
            _run(["npm", "install", "--silent", "--no-audit", "--no-fund"], root, timeout=120)

    if not node_modules.exists():
        result.tools_skipped.append("tsc (dependencies not installed)")
        return

    # Correr tsc --noEmit si existe
    tsc_bin = node_modules / ".bin" / ("tsc.cmd" if _has_command("cmd") and (node_modules / ".bin" / "tsc.cmd").exists() else "tsc")
    if not tsc_bin.exists():
        # Fallback: npx
        if _has_command("npx"):
            result.tools_run.append("tsc (via npx)")
            code, stdout, stderr = _run(["npx", "--no-install", "tsc", "--noEmit"], root, timeout=120)
        else:
            result.tools_skipped.append("tsc (no npx)")
            return
    else:
        result.tools_run.append("tsc")
        code, stdout, stderr = _run([str(tsc_bin), "--noEmit"], root, timeout=120)

    # Parsear errores tsc: formato "path(L,C): error TSXXXX: message"
    combined = stdout + "\n" + stderr
    for line in combined.splitlines():
        m = re.match(r"^(.+?)\((\d+),(\d+)\):\s*(error|warning)\s+TS\d+:\s*(.+)$", line)
        if m:
            result.issues.append(ValidationIssue(
                tool="tsc",
                file=m.group(1).replace(str(root), "").lstrip("/\\").replace("\\", "/"),
                line=int(m.group(2)),
                severity=m.group(4),
                message=m.group(5).strip()[:200],
            ))


def _validate_go(root: Path, files: List[Path], result: ValidationResult) -> None:
    if not _has_command("go"):
        result.tools_skipped.append("go (not installed)")
        return

    result.tools_run.append("go vet")
    code, stdout, stderr = _run(["go", "vet", "./..."], root, timeout=60)
    combined = stdout + "\n" + stderr
    for line in combined.splitlines():
        m = re.match(r"^(.+?):(\d+):(\d+):\s*(.+)$", line)
        if m:
            result.issues.append(ValidationIssue(
                tool="go vet",
                file=m.group(1),
                line=int(m.group(2)),
                severity="error",
                message=m.group(4).strip()[:200],
            ))

    result.tools_run.append("go build")
    code, stdout, stderr = _run(["go", "build", "./..."], root, timeout=120)
    if code != 0:
        combined = stdout + "\n" + stderr
        for line in combined.splitlines():
            m = re.match(r"^(.+?):(\d+):(\d+):\s*(.+)$", line)
            if m:
                result.issues.append(ValidationIssue(
                    tool="go build",
                    file=m.group(1),
                    line=int(m.group(2)),
                    severity="error",
                    message=m.group(4).strip()[:200],
                ))


def _validate_rust(root: Path, files: List[Path], result: ValidationResult) -> None:
    if not _has_command("cargo"):
        result.tools_skipped.append("cargo (not installed)")
        return
    result.tools_run.append("cargo check")
    code, stdout, stderr = _run(["cargo", "check", "--message-format=short"], root, timeout=180)
    combined = stdout + "\n" + stderr
    for line in combined.splitlines():
        if "error" in line and ":" in line:
            result.issues.append(ValidationIssue(
                tool="cargo check",
                file="",
                line=None,
                severity="error",
                message=line.strip()[:200],
            ))


# ── API pública ──────────────────────────────────────────────────────


def validate_project(artifacts_dir: str | Path, *, enabled: bool = True) -> ValidationResult:
    """Detecta el stack y corre los validadores disponibles en el sistema.

    Args:
        artifacts_dir: Carpeta con los archivos generados del proyecto.
        enabled: Si es False, devuelve un resultado vacío (feature flag).

    Returns:
        ValidationResult con issues encontrados y metadatos.
    """
    result = ValidationResult()

    if not enabled:
        return result

    root = Path(artifacts_dir).resolve()
    if not root.exists():
        return result

    language, files = _detect_language(root)
    logger.info("Code validator: language=%s files=%d", language, len(files))

    if language == "python":
        _validate_python(root, files, result)
    elif language in {"typescript", "javascript"}:
        _validate_typescript(root, files, result)
    elif language == "go":
        _validate_go(root, files, result)
    elif language == "rust":
        _validate_rust(root, files, result)
    else:
        result.tools_skipped.append(f"{language} (no validator configured)")

    # Cap total issues to avoid spam
    if len(result.issues) > 50:
        remaining = len(result.issues) - 50
        result.issues = result.issues[:50]
        result.issues.append(ValidationIssue(
            tool="code_validator",
            file="",
            line=None,
            severity="warning",
            message=f"+ {remaining} issues más truncados para mantener feedback accionable",
        ))

    return result
