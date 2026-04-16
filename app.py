"""DevTeam AI — Plataforma de Desarrollo de Software Multi-Agente.

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4

# ── Asegurar que el root del proyecto este en sys.path ──────────────
_ROOT = str(Path(__file__).resolve().parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Cargar .env en variables de entorno (necesario para SDKs de LLM) ─
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

import streamlit as st  # noqa: E402

from src.config.settings import get_settings  # noqa: E402
from src.orchestrator.team import create_dev_team  # noqa: E402
from src.storage.memory_integration import MemoryIntegration  # noqa: E402
from src.storage.database import get_database  # noqa: E402
from src.storage.session_manager import SessionManager  # noqa: E402
from src.storage.artifact_monitor import ArtifactMonitor  # noqa: E402

from agno.models.message import Message  # noqa: E402

# ── Configuracion de pagina ─────────────────────────────────────────

st.set_page_config(
    page_title="DevTeam AI",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estado de sesion por defecto ────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())
if "user_id" not in st.session_state:
    st.session_state.user_id = "default-user"
if "artifacts" not in st.session_state:
    st.session_state.artifacts = []
if "team" not in st.session_state:
    st.session_state.team = None
if "memory" not in st.session_state:
    st.session_state.memory = None
if "session_manager" not in st.session_state:
    st.session_state.session_manager = None
if "artifact_monitor" not in st.session_state:
    st.session_state.artifact_monitor = None

# ── Configuracion ───────────────────────────────────────────────────

settings = get_settings()

# ── Inicializar gestores de memoria ─────────────────────────────────

if st.session_state.memory is None:
    st.session_state.memory = MemoryIntegration(settings, project_id=st.session_state.session_id)

if st.session_state.session_manager is None:
    db = get_database(settings)
    st.session_state.session_manager = SessionManager(db)

if st.session_state.artifact_monitor is None and st.session_state.memory:
    st.session_state.artifact_monitor = ArtifactMonitor(
        artifacts_path=settings.artifacts_path,
        memory=st.session_state.memory
    )

# ── Barra lateral ───────────────────────────────────────────────────

with st.sidebar:
    st.title("🏗️ DevTeam AI")
    st.caption("Tu equipo de desarrollo con IA")
    st.divider()

    # -- Configuracion ------------------------------------------------
    st.subheader("⚙️ Configuracion")

    provider_options = ["ollama", "openai", "anthropic", "google"]
    provider = st.selectbox(
        "Proveedor LLM",
        options=provider_options,
        index=(
            provider_options.index(settings.llm_provider)
            if settings.llm_provider in provider_options
            else 0
        ),
    )
    model_id = st.text_input("Modelo", value=settings.llm_model)
    orch_model = st.text_input("Modelo del Orquestador", value=settings.orchestrator_model)
    ollama_host = settings.ollama_host
    if provider == "ollama":
        ollama_host = st.text_input("Host de Ollama", value=settings.ollama_host)

    st.divider()

    # -- Gestion de sesion --------------------------------------------
    st.subheader("💬 Sesion")
    user_id = st.text_input("Tu nombre", value=st.session_state.user_id)
    st.session_state.user_id = user_id

    if st.button("🔄 Nueva conversacion", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid4())
        st.session_state.artifacts = []
        st.session_state.team = None
        # Reiniciar memoria con nuevo project_id
        st.session_state.memory = MemoryIntegration(settings, project_id=st.session_state.session_id)
        # Reiniciar monitor de artefactos
        if st.session_state.memory:
            st.session_state.artifact_monitor = ArtifactMonitor(
                artifacts_path=settings.artifacts_path,
                memory=st.session_state.memory
            )
        st.rerun()

    st.caption(f"Sesion: `{st.session_state.session_id[:8]}...`")
    
    # Mostrar estado de memoria vectorizada
    if st.session_state.memory and st.session_state.memory.is_enabled():
        st.caption("🧠 Memoria vectorizada: ✅ Activa")
    else:
        st.caption("🧠 Memoria vectorizada: ⚪ Desactivada")

    st.divider()

    # -- Info del pipeline --------------------------------------------
    st.subheader("🔀 Como funciona")
    st.markdown(
        """
        1. 💬 **Conversacion** — Te guio paso a paso
        2. 📋 **Analisis** — Requisitos claros
        3. 📐 **Diseno** — Arquitectura solida
        4. 💻 **Codigo** — Implementacion real
        5. ✅ **Validacion** — QA y Seguridad
        """
    )

    # -- Lista de artefactos ------------------------------------------
    artifacts_path = settings.artifacts_path
    if artifacts_path.exists():
        files = sorted(
            str(f.relative_to(artifacts_path)).replace("\\", "/")
            for f in artifacts_path.rglob("*")
            if f.is_file() and f.name != ".gitkeep"
        )
        if files:
            st.divider()
            st.subheader(f"📁 Archivos generados ({len(files)})")
            for fname in files:
                st.text(f"  📄 {fname}")

# ── Verificacion de proveedor ───────────────────────────────────────


def _provider_ready(selected_provider: str) -> bool:
    if selected_provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if selected_provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if selected_provider == "google":
        return bool(os.environ.get("GOOGLE_API_KEY"))
    if selected_provider == "ollama":
        return True
    return False


_provider_is_ready = _provider_ready(provider)

# ── Area de contenido principal ─────────────────────────────────────

st.title("🏗️ DevTeam AI")
st.markdown(
    "**¡Hola!** Soy tu equipo de desarrollo con IA. "
    "Cuentame que quieres construir y te guiare paso a paso. "
    "No necesitas saber de programacion — **yo te pregunto todo lo necesario.**"
)
st.divider()

if not _provider_is_ready:
    st.warning(
        "⚠️ Faltan credenciales para el proveedor seleccionado. "
        "Configura la clave correspondiente en `.env`: "
        "`OPENAI_API_KEY`, `ANTHROPIC_API_KEY` o `GOOGLE_API_KEY`."
    )
    st.stop()

# ── Mensaje de bienvenida inicial ───────────────────────────────────

if not st.session_state.messages:
    welcome = (
        "👋 **¡Bienvenido a DevTeam AI!**\n\n"
        "Soy tu asistente de desarrollo de software. "
        "Mi trabajo es ayudarte a construir tu proyecto paso a paso, "
        "sin importar tu nivel tecnico.\n\n"
        "**¿Que te gustaria crear hoy?** Puede ser cualquier cosa:\n"
        "- Una pagina web\n"
        "- Una aplicacion movil\n"
        "- Un sistema de gestion\n"
        "- Una API\n"
        "- ¡Lo que necesites!\n\n"
        "Simplemente cuentame tu idea con tus propias palabras y yo me "
        "encargo de hacer las preguntas necesarias. 😊"
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# ── Historial de chat ───────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Entrada de chat y procesamiento ─────────────────────────────────

if prompt := st.chat_input("Escribi tu idea o responde las preguntas..."):
    # Mostrar mensaje del usuario inmediatamente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar con el equipo de desarrollo
    with st.chat_message("assistant"):
        with st.spinner("🤔 Pensando..."):
            try:
                # Reusar o crear el equipo (mantiene historial de conversacion)
                if st.session_state.team is None:
                    st.session_state.team = create_dev_team(
                        overrides={
                            "llm_provider": provider,
                            "llm_model": model_id,
                            "orchestrator_model": orch_model,
                            "ollama_host": ollama_host,
                        },
                        session_id=st.session_state.session_id,  # ← Pasar session_id
                    )

                team = st.session_state.team

                # Construir historial completo como List[Message]
                # para que el orquestador SIEMPRE tenga contexto
                messages: list[Message] = []
                for msg in st.session_state.messages:
                    # Saltar el mensaje de bienvenida (ya esta en las instrucciones)
                    if msg["role"] == "assistant" and msg is st.session_state.messages[0]:
                        continue
                    messages.append(
                        Message(role=msg["role"], content=msg["content"])
                    )

                result = team.run(
                    messages,
                    user_id=st.session_state.user_id,
                    session_id=st.session_state.session_id,
                    stream=False,
                )
                
                # Almacenar en memoria vectorizada
                memory = st.session_state.memory
                if memory and memory.is_enabled():
                    # Almacenar mensaje del usuario
                    memory.store_conversation_message(
                        session_id=st.session_state.session_id,
                        role="user",
                        content=prompt
                    )
                    
                    # Almacenar respuesta del asistente
                    if result and result.content:
                        memory.store_conversation_message(
                            session_id=st.session_state.session_id,
                            role="assistant",
                            content=result.content
                        )
                        
                        # Detectar y almacenar artefactos específicos
                        response_lower = result.content.lower()
                        
                        # Si es documento de requisitos
                        if "requisitos funcionales" in response_lower or "rf-" in response_lower:
                            memory.store_requirements(
                                session_id=st.session_state.session_id,
                                requirements_doc=result.content
                            )
                        
                        # Si es documento de diseño
                        if "arquitectura" in response_lower or "adr-" in response_lower:
                            memory.store_design_components(
                                session_id=st.session_state.session_id,
                                design_doc=result.content
                            )
                        
                        # Escanear y almacenar artefactos generados
                        if st.session_state.artifact_monitor:
                            st.session_state.artifact_monitor.scan_and_store(
                                session_id=st.session_state.session_id
                            )

            except Exception as exc:
                st.error(f"Error: {exc}")
                import traceback
                st.code(traceback.format_exc())
                st.stop()

        # Mostrar la respuesta
        response_text = (
            result.content if result and result.content else "No se genero respuesta."
        )
        st.markdown(response_text)

        # Persistir en historial
        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )

        # Mostrar artefactos generados (si los hay)
        if artifacts_path.exists():
            generated = sorted(
                str(f.relative_to(artifacts_path)).replace("\\", "/")
                for f in artifacts_path.rglob("*")
                if f.is_file() and f.name != ".gitkeep"
            )
            if generated:
                with st.expander(
                    f"📁 Archivos generados ({len(generated)})",
                    expanded=False,
                ):
                    for fname in generated:
                        file_path = artifacts_path / fname
                        lang = fname.rsplit(".", 1)[-1] if "." in fname else ""
                        st.markdown(f"**`{fname}`**")
                        try:
                            st.code(
                                file_path.read_text(encoding="utf-8"),
                                language=lang,
                            )
                        except Exception:
                            st.text("(no se pudo leer el archivo)")
