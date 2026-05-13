"""Analizador de la conversación previa al pipeline.

Extrae señales concretas del diálogo usuario-orquestador que el pipeline
debe respetar: stack acordado, funcionalidades mencionadas, entidades,
tipo de proyecto. La idea es que el resto del pipeline no tenga que
adivinar ni improvisar sobre lo que el usuario ya dejó claro.

Implementación deliberadamente basada en reglas para no depender del LLM:
rápido, determinista y fácil de testear.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ── Catálogos de detección ──────────────────────────────────────────


_STACK_HINTS = {
    # Frontend
    "react_vite": ["react + vite", "react con vite", "vite + react"],
    "nextjs": ["next.js", "nextjs", "next 14", "next 13"],
    "vue3": ["vue 3", "vue3", "vuejs", "vue.js"],
    "svelte": ["svelte", "sveltekit"],
    "react_native": ["react native", "expo"],
    # Backend
    "express": ["express", "node.js con express", "nodejs con express", "node + express"],
    "fastify": ["fastify"],
    "nestjs": ["nestjs", "nest.js"],
    "fastapi": ["fastapi", "fast api"],
    "django": ["django"],
    "flask": ["flask"],
    "chi": ["go chi", " chi "],
    "gin": ["go gin", "gin-gonic"],
    "rails": ["ruby on rails", " rails "],
    "laravel": ["laravel"],
    "spring": ["spring boot", "springboot"],
    # Databases
    "postgresql": ["postgres", "postgresql"],
    "mysql": ["mysql", "mariadb"],
    "mongodb": ["mongodb", "mongo"],
    "sqlite": ["sqlite"],
    "redis": ["redis"],
    "supabase": ["supabase"],
    "firebase": ["firebase", "firestore"],
}

_LANGUAGE_OF_STACK = {
    "react_vite": "typescript",
    "nextjs": "typescript",
    "vue3": "typescript",
    "svelte": "typescript",
    "react_native": "typescript",
    "express": "typescript",
    "fastify": "typescript",
    "nestjs": "typescript",
    "fastapi": "python",
    "django": "python",
    "flask": "python",
    "chi": "go",
    "gin": "go",
    "rails": "ruby",
    "laravel": "php",
    "spring": "java",
}

_BACKEND_STACKS = {"express", "fastify", "nestjs", "fastapi", "django", "flask", "chi", "gin", "rails", "laravel", "spring"}
_FRONTEND_STACKS = {"react_vite", "nextjs", "vue3", "svelte", "react_native"}
_DATABASES = {"postgresql", "mysql", "mongodb", "sqlite", "redis", "supabase", "firebase"}
_MOBILE_STACKS = {"react_native"}


# ── Señales del tipo de proyecto ────────────────────────────────────


_PROJECT_TYPE_SIGNALS = {
    "mobile_app": [
        "app móvil", "app movil", "aplicación móvil", "aplicacion movil",
        "android", "ios", "react native", "expo", "flutter",
    ],
    "cli_tool": ["cli", "línea de comandos", "linea de comandos", "terminal"],
    "data_pipeline": ["etl", "pipeline de datos", "procesamiento de datos"],
    "ml_model": ["machine learning", " ml ", "modelo de ia", "predicción"],
    "api_rest": ["api rest", "api pública", "solo api", "solo backend", "microservicio"],
}


# ── Modelo de resultado ──────────────────────────────────────────────


@dataclass
class ConversationInsights:
    """Señales extraídas de la conversación con el usuario."""

    project_type_hint: Optional[str] = None
    user_frontend: Optional[str] = None
    user_backend: Optional[str] = None
    user_database: Optional[str] = None
    user_language: Optional[str] = None
    user_mobile: bool = False
    mentioned_features: List[str] = field(default_factory=list)
    mentioned_entities: List[str] = field(default_factory=list)
    raw_user_text: str = ""

    def render_stack_directive(self) -> str:
        """Produce un bloque de texto que se inyecta al diseño para FORZAR respetar el stack."""
        parts: List[str] = []
        parts.append(
            "STACK ACORDADO EN LA CONVERSACIÓN (RESPÉTALO EXACTAMENTE):"
        )
        if self.user_language:
            parts.append(f"- Lenguaje: {self.user_language}")
        if self.user_backend:
            parts.append(f"- Backend: {self.user_backend}")
        if self.user_frontend:
            parts.append(f"- Frontend: {self.user_frontend}")
        if self.user_database:
            parts.append(f"- Base de datos: {self.user_database}")
        if self.project_type_hint:
            parts.append(f"- Tipo de proyecto: {self.project_type_hint}")
        if len(parts) == 1:
            return ""  # No hay stack acordado, dejar libre
        parts.append(
            "\nNO cambies el stack por otro. Si hay restricciones que impiden usarlo, "
            "márcalo explícitamente como un ADR pero mantén la elección del usuario."
        )
        return "\n".join(parts)

    def render_features_directive(self) -> str:
        """Lista de funcionalidades mencionadas para orientar análisis y diseño."""
        if not self.mentioned_features and not self.mentioned_entities:
            return ""
        parts = ["FUNCIONALIDADES Y ENTIDADES MENCIONADAS POR EL USUARIO:"]
        if self.mentioned_features:
            parts.append("Funcionalidades explícitas:")
            for feat in self.mentioned_features:
                parts.append(f"  - {feat}")
        if self.mentioned_entities:
            parts.append("Entidades del dominio detectadas:")
            for ent in self.mentioned_entities:
                parts.append(f"  - {ent}")
        parts.append(
            "\nTodas estas funcionalidades DEBEN existir en el código generado. "
            "No te quedes con el formulario de contacto: implementa TODO el catálogo."
        )
        return "\n".join(parts)


# ── Heurísticas de extracción ───────────────────────────────────────


_FEATURE_PATTERNS = [
    (r"\b(cat[aá]logo)\b", "Catálogo (listado con productos)"),
    (r"\b(b[uú]squeda|buscador)\b", "Búsqueda"),
    (r"\b(filtr(o|ar|ado))\b", "Filtrado"),
    (r"\b(detalle(s)? del producto|ficha)\b", "Detalle de producto"),
    (r"\b(carrito)\b", "Carrito de compras"),
    (r"\b(checkout|pago|pasarela)\b", "Checkout / pasarela de pago"),
    (r"\b(login|iniciar sesi[oó]n|autenticaci[oó]n)\b", "Autenticación (login)"),
    (r"\b(registro|registrarse|sign ?up)\b", "Registro de usuarios"),
    (r"\b(roles?|permisos|admin)\b", "Roles y permisos"),
    (r"\b(dashboard|panel)\b", "Dashboard / panel de control"),
    (r"\b(reportes?|estad[ií]sticas?)\b", "Reportes / estadísticas"),
    (r"\b(contacto|formulario de contacto)\b", "Formulario de contacto"),
    (r"\b(perfil de usuario|mi perfil)\b", "Perfil de usuario"),
    (r"\b(notificaciones?)\b", "Notificaciones"),
    (r"\b(chat|mensajer[ií]a)\b", "Chat / mensajería"),
    (r"\b(inventario|stock)\b", "Inventario / control de stock"),
    (r"\b(pedidos?|[oó]rdenes?)\b", "Pedidos / órdenes"),
    (r"\b(reservas?|agenda|citas?)\b", "Reservas / agenda"),
    (r"\b(responsive|m[oó]vil y web)\b", "Responsive (web + móvil)"),
    (r"\b(subida de archivos?|upload|im[aá]genes?)\b", "Subida de archivos / imágenes"),
]


_ENTITY_KEYWORDS = [
    # Dominio común detectable por sustantivos clave
    "producto", "productos", "cliente", "clientes", "usuario", "usuarios",
    "pedido", "pedidos", "orden", "órdenes", "factura", "facturas",
    "categoría", "categorías", "carrito", "stock", "inventario",
    "reserva", "reservas", "cita", "citas", "evento", "eventos",
    "mensaje", "mensajes", "comentario", "comentarios", "post", "posts",
    "proyecto", "proyectos", "tarea", "tareas", "empleado", "empleados",
    "vehículo", "vehículos", "habitación", "habitaciones",
    "curso", "cursos", "estudiante", "estudiantes", "profesor", "profesores",
]


def _extract_user_only(full_conversation: str) -> str:
    """Devuelve solo los mensajes del usuario (ignora assistant)."""
    user_blocks: List[str] = []
    # formato esperado: "user: ... \n assistant: ... \n user: ..."
    pattern = re.compile(r"^(user|usuario):\s*(.+?)(?=^\s*(?:user|usuario|assistant|ai|bot):|\Z)",
                         re.IGNORECASE | re.MULTILINE | re.DOTALL)
    matches = pattern.findall(full_conversation)
    for _role, content in matches:
        user_blocks.append(content.strip())
    if user_blocks:
        return "\n".join(user_blocks)
    return full_conversation


def _detect_first_stack(text: str, keys: set[str]) -> Optional[str]:
    """Busca la primera mención de cualquier stack del set `keys`."""
    lowered = text.lower()
    earliest_idx = len(text) + 1
    found: Optional[str] = None
    for key in keys:
        for hint in _STACK_HINTS.get(key, []):
            idx = lowered.find(hint.lower())
            if idx >= 0 and idx < earliest_idx:
                earliest_idx = idx
                found = key
    return found


def analyze_conversation(full_conversation: str) -> ConversationInsights:
    """Extrae insights estructurados de la conversación completa."""
    user_text = _extract_user_only(full_conversation)
    lowered = user_text.lower()

    # Tipo de proyecto
    project_type_hint: Optional[str] = None
    for ptype, signals in _PROJECT_TYPE_SIGNALS.items():
        if any(s in lowered for s in signals):
            project_type_hint = ptype
            break

    # Stack preferido
    backend = _detect_first_stack(full_conversation, _BACKEND_STACKS)
    frontend = _detect_first_stack(full_conversation, _FRONTEND_STACKS)
    database = _detect_first_stack(full_conversation, _DATABASES)
    mobile_hit = _detect_first_stack(full_conversation, _MOBILE_STACKS)

    # Lenguaje inferido: priorizar backend si existe
    language: Optional[str] = None
    if backend:
        language = _LANGUAGE_OF_STACK.get(backend)
    elif frontend:
        language = _LANGUAGE_OF_STACK.get(frontend)

    # Corrección: si hay backend python pero frontend react/next, language sigue siendo python (backend)
    # y el frontend se documenta aparte

    # Si mencionó react native o expo, es mobile
    if mobile_hit:
        project_type_hint = "mobile_app"
        frontend = "react_native"
        language = "typescript"

    # Funcionalidades
    features: List[str] = []
    seen: set[str] = set()
    for pattern, label in _FEATURE_PATTERNS:
        if re.search(pattern, user_text, re.IGNORECASE):
            if label not in seen:
                features.append(label)
                seen.add(label)

    # Entidades (usamos singular + plural, deduplicado a singular)
    entities: List[str] = []
    ent_seen: set[str] = set()
    for word in _ENTITY_KEYWORDS:
        if re.search(rf"\b{word}\b", lowered):
            # normalizar a singular sencillo
            sing = word.rstrip("s").rstrip("e") if word.endswith("es") else word.rstrip("s")
            if sing and sing not in ent_seen:
                entities.append(sing)
                ent_seen.add(sing)

    return ConversationInsights(
        project_type_hint=project_type_hint,
        user_frontend=frontend,
        user_backend=backend,
        user_database=database,
        user_language=language,
        user_mobile=bool(mobile_hit),
        mentioned_features=features,
        mentioned_entities=entities,
        raw_user_text=user_text[:2000],
    )
