"""Detector de stack a partir del documento de diseño.

Extrae el CONTRATO DE IMPLEMENTACIÓN (sección 11) generado por el agente
de diseño y lo convierte en un StackProfile. Si la sección está ausente
o incompleta, aplica heurísticas sobre el texto completo del diseño para
inferir los valores con el mejor esfuerzo posible.
"""

from __future__ import annotations

import re
from typing import Optional

from src.agents.prompts.selector import StackProfile


# ── Diccionarios de normalización ───────────────────────────────────

_PROJECT_TYPE_ALIASES = {
    "api": "api_rest",
    "rest": "api_rest",
    "api_rest": "api_rest",
    "api rest": "api_rest",
    "backend": "api_rest",
    "web": "web_app",
    "web app": "web_app",
    "web_app": "web_app",
    "webapp": "web_app",
    "website": "web_app",
    "frontend": "web_app",
    "fullstack": "fullstack",
    "full-stack": "fullstack",
    "full stack": "fullstack",
    "mobile": "mobile_app",
    "mobile_app": "mobile_app",
    "móvil": "mobile_app",
    "app móvil": "mobile_app",
    "cli": "cli_tool",
    "cli_tool": "cli_tool",
    "terminal": "cli_tool",
    "data": "data_pipeline",
    "etl": "data_pipeline",
    "pipeline": "data_pipeline",
    "data_pipeline": "data_pipeline",
    "ml": "ml_model",
    "machine learning": "ml_model",
    "ml_model": "ml_model",
    "desktop": "desktop_app",
    "desktop_app": "desktop_app",
    "library": "library",
    "librería": "library",
}

_LANGUAGE_KEYWORDS = {
    "python": ["python", "fastapi", "django", "flask", "pyramid", "pytest", "pandas"],
    "typescript": ["typescript", "ts-node", "tsconfig"],
    "javascript": ["javascript", "node.js", "nodejs"],
    "go": ["golang", " go ", "go modules"],
    "rust": ["rust", "cargo"],
    "java": ["java ", "spring", "maven", "gradle"],
    "kotlin": ["kotlin"],
    "csharp": ["c#", "asp.net", ".net"],
    "ruby": ["ruby", "rails"],
    "php": ["php", "laravel", "symfony"],
}

_BACKEND_FRAMEWORK_KEYWORDS = {
    "fastapi": ["fastapi"],
    "django": ["django"],
    "flask": ["flask"],
    "express": ["express.js", "expressjs", "express "],
    "fastify": ["fastify"],
    "nestjs": ["nestjs", "nest.js"],
    "chi": ["chi router", " chi "],
    "gin": [" gin ", "gin-gonic"],
    "echo": [" echo ", "labstack"],
    "fiber": ["gofiber", " fiber "],
    "spring": ["spring boot", "spring-boot"],
    "rails": ["ruby on rails", " rails "],
    "laravel": ["laravel"],
}

_FRONTEND_FRAMEWORK_KEYWORDS = {
    "nextjs": ["next.js", "nextjs", "next 14", "next 13", "app router"],
    "react_vite": ["react + vite", "vite", "react 18"],
    "vue3": ["vue 3", "vue3", "vue.js 3", "composition api"],
    "svelte": ["svelte", "sveltekit"],
    "react_native": ["react native", "expo"],
    "angular": ["angular"],
    "solid": ["solidjs", "solid.js"],
    "astro": ["astro"],
}

_DATABASE_KEYWORDS = {
    "postgresql": ["postgres", "postgresql", "pgvector"],
    "mysql": ["mysql", "mariadb"],
    "mongodb": ["mongodb", "mongo", "mongoose"],
    "sqlite": ["sqlite"],
    "redis": ["redis"],
    "dynamodb": ["dynamodb"],
    "firestore": ["firestore", "firebase"],
}


# ── Utilidades de extracción ────────────────────────────────────────


def _extract_section(text: str, header_pattern: str) -> Optional[str]:
    """Extrae el contenido bajo un encabezado markdown hasta el siguiente de su nivel."""
    match = re.search(rf"^{header_pattern}.*$", text, re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    start = match.end()
    # buscar siguiente encabezado del mismo o mayor nivel
    header_level = header_pattern.count("#")
    next_header = re.search(
        rf"^#{{1,{header_level}}}\s", text[start:], re.MULTILINE
    )
    end = start + next_header.start() if next_header else len(text)
    return text[start:end]


def _extract_kv(block: str, key: str) -> Optional[str]:
    """Busca líneas tipo 'KEY: valor' dentro del bloque."""
    pattern = rf"{re.escape(key)}\s*:\s*([^\n]+)"
    match = re.search(pattern, block, re.IGNORECASE)
    if not match:
        return None
    value = match.group(1).strip().strip("[]`*")
    # descartar placeholders
    if value.lower() in {"ninguno", "none", "n/a", "-", ""}:
        return None
    # tomar solo la primera opción si es una lista separada por |
    if "|" in value:
        first = value.split("|")[0].strip()
        if first.lower() not in {"ninguno", "none"}:
            return first
    return value


def _first_keyword_match(text: str, mapping: dict[str, list[str]]) -> Optional[str]:
    """Devuelve la primera clave cuyo keyword aparece en el texto."""
    lowered = text.lower()
    for key, patterns in mapping.items():
        for pattern in patterns:
            if pattern.lower() in lowered:
                return key
    return None


def _normalize_project_type(raw: Optional[str]) -> str:
    if not raw:
        return "fullstack"
    key = raw.strip().lower()
    return _PROJECT_TYPE_ALIASES.get(key, key.replace(" ", "_"))


# ── API pública ──────────────────────────────────────────────────────


def detect_stack(design_doc: str, user_context: str = "") -> StackProfile:
    """Construye un StackProfile a partir del diseño (y contexto opcional)."""
    contract = _extract_section(design_doc, r"##\s+11\.?\s+CONTRATO DE IMPLEMENTACI")
    # si no encontró el encabezado literal, busca la versión sin número
    if contract is None:
        contract = _extract_section(design_doc, r"##\s+CONTRATO DE IMPLEMENTACI")

    # Valores desde el contrato si existen
    project_type = None
    language = None
    backend_framework = None
    frontend_framework = None
    database = None

    if contract:
        project_type = _extract_kv(contract, "PROJECT_TYPE")
        language = _extract_kv(contract, "LANGUAGE")
        backend_framework = _extract_kv(contract, "BACKEND_FRAMEWORK")
        frontend_framework = _extract_kv(contract, "FRONTEND_FRAMEWORK")
        database = _extract_kv(contract, "DATABASE")

    full_text = f"{design_doc}\n{user_context}"

    # Heurística de respaldo si falta cualquier campo
    if not language:
        language = _first_keyword_match(full_text, _LANGUAGE_KEYWORDS)
    if not backend_framework:
        backend_framework = _first_keyword_match(full_text, _BACKEND_FRAMEWORK_KEYWORDS)
    if not frontend_framework:
        frontend_framework = _first_keyword_match(full_text, _FRONTEND_FRAMEWORK_KEYWORDS)
    if not database:
        database = _first_keyword_match(full_text, _DATABASE_KEYWORDS)

    # Inferir project_type si no vino
    if not project_type:
        lowered = full_text.lower()
        # Mobile tiene prioridad si el frontend es react_native o similar
        if frontend_framework and frontend_framework.lower() in {"react_native", "expo", "flutter"}:
            project_type = "mobile_app"
        elif any(k in lowered for k in [" cli", "typer", "click ", "commander", "herramienta de l", "línea de comandos", "terminal tool"]):
            project_type = "cli_tool"
        elif any(k in lowered for k in ["pipeline etl", " etl ", "airflow", "prefect", "dagster", "pandas pipeline", "procesamiento batch"]):
            project_type = "data_pipeline"
        elif any(k in lowered for k in ["machine learning", " modelo ml", "scikit-learn", " mlflow", " xgboost", " pytorch"]):
            project_type = "ml_model"
        elif backend_framework and frontend_framework:
            project_type = "fullstack"
        elif frontend_framework and not backend_framework:
            project_type = "web_app"
        elif backend_framework and not frontend_framework:
            project_type = "api_rest"
        elif _first_keyword_match(full_text, {"mobile_app": ["react native", "expo", "flutter"]}):
            project_type = "mobile_app"
        else:
            project_type = "fullstack"

    return StackProfile(
        project_type=_normalize_project_type(project_type),
        language=(language or "typescript").lower(),
        backend_framework=backend_framework.lower() if backend_framework else None,
        frontend_framework=frontend_framework.lower() if frontend_framework else None,
        database=database.lower() if database else None,
    )
