"""DevTeam AI — Plataforma de Desarrollo de Software Multi-Agente.

Ejecutar con:  streamlit run app.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from uuid import uuid4
import warnings

# Silenciar warnings de transformers/torchvision
warnings.filterwarnings("ignore", category=UserWarning, module="transformers")
warnings.filterwarnings("ignore", message=".*torchvision.*")

# Silenciar logs ruidosos de HuggingFace y sentence-transformers
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

import logging  # noqa: E402
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

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
from src.orchestrator.pipeline import run_pipeline, NullReporter  # noqa: E402
from src.storage.memory_integration import MemoryIntegration  # noqa: E402
from src.storage.database import get_database  # noqa: E402
from src.storage.session_manager import SessionManager  # noqa: E402
from src.storage.artifact_monitor import ArtifactMonitor  # noqa: E402
from src.storage.knowledge_memory import KnowledgeMemory  # noqa: E402
from src.agents.learning import LearningAgent  # noqa: E402
from src.agents.analysis import create_analysis_agent  # noqa: E402

from agno.models.message import Message  # noqa: E402

# ── Configuracion de pagina ─────────────────────────────────────────

st.set_page_config(
    page_title="DevTeam AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Estado de sesion por defecto ────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())
if "project_name" not in st.session_state:
    st.session_state.project_name = None  # Se definirá cuando el usuario confirme el proyecto
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
if "knowledge" not in st.session_state:
    st.session_state.knowledge = None
if "learning_agent" not in st.session_state:
    st.session_state.learning_agent = None

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

# Inicializar base de conocimiento y agente de aprendizaje
if st.session_state.knowledge is None and settings.supabase_db_url:
    try:
        km = KnowledgeMemory(settings.supabase_db_url)
        km.ensure_table()
        st.session_state.knowledge = km
        st.session_state.learning_agent = LearningAgent(settings, km)
        # Mantenimiento periódico: decay + consolidación (solo una vez por sesión)
        if not st.session_state.get("_knowledge_maintained"):
            try:
                maint_stats = st.session_state.learning_agent.periodic_maintenance()
                logger.info(
                    "Mantenimiento de conocimiento: decay=%d consolidados=%d",
                    maint_stats.get("decay_affected", 0),
                    maint_stats.get("consolidated", 0),
                )
                st.session_state._knowledge_maintained = True
            except Exception as _me:
                logger.warning(f"Mantenimiento falló: {_me}")
    except Exception as _e:
        logger.warning(f"No se pudo inicializar KnowledgeMemory: {_e}")

# ── Barra lateral ───────────────────────────────────────────────────

with st.sidebar:
    st.title("DevTeam AI")
    st.divider()

    # -- Configuracion ------------------------------------------------
    st.subheader("Configuración")

    provider_options = ["groq", "openai", "ollama", "anthropic", "google"]
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
    st.subheader("Sesión")
    user_id = st.text_input("Usuario", value=st.session_state.user_id)
    st.session_state.user_id = user_id
    
    # -- Ruta de artefactos -------------------------------------------
    st.subheader("Directorio de salida")
    
    # Obtener ruta actual
    current_artifacts = str(settings.artifacts_path)
    
    # Opciones rápidas
    quick_paths = {
        "Proyecto (por defecto)": "artifacts",
        "Escritorio": f"C:/Users/{os.environ.get('USERNAME', 'estra')}/Desktop/ProyectosIA",
        "Documentos": f"C:/Users/{os.environ.get('USERNAME', 'estra')}/Documents/DevTeamProjects",
        "Personalizada": "custom"
    }
    
    selected_option = st.selectbox(
        "Ubicación",
        options=list(quick_paths.keys()),
        index=0
    )
    
    # Si selecciona personalizada, mostrar input
    if selected_option == "Personalizada":
        artifacts_input = st.text_input(
            "Ruta",
            value=current_artifacts,
            placeholder="C:/Users/usuario/proyectos"
        )
    else:
        artifacts_input = quick_paths[selected_option]
        st.caption(f"Ruta: `{artifacts_input}`")
    
    # Botón para aplicar cambio de ruta
    if st.button("Aplicar Ruta", use_container_width=True):
        if artifacts_input and artifacts_input != current_artifacts:
            # Actualizar en .env
            os.environ["ARTIFACTS_DIR"] = artifacts_input
            
            # Forzar recarga de settings
            from src.config.settings import get_settings
            get_settings.cache_clear()
            
            st.success(f"Ruta actualizada")
            st.rerun()
    
    st.caption(f"`{current_artifacts}`")
    st.divider()

    if st.button("Nueva sesión", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid4())
        st.session_state.project_name = None
        st.session_state.artifacts = []
        st.session_state.team = None
        st.session_state.memory = MemoryIntegration(settings, project_id=st.session_state.session_id)
        if st.session_state.memory:
            st.session_state.artifact_monitor = ArtifactMonitor(
                artifacts_path=settings.artifacts_path,
                memory=st.session_state.memory
            )
        # knowledge y learning_agent se reusan entre sesiones (son globales al sistema)
        st.rerun()

    st.caption(f"Sesión: `{st.session_state.session_id[:8]}`")
    
    # Mostrar nombre del proyecto si existe
    if st.session_state.project_name:
        st.caption(f"Proyecto: `{st.session_state.project_name}`")
    
    st.divider()

    # -- Info del pipeline --------------------------------------------
    st.subheader("Fases")
    st.markdown(
        """
        1. Análisis
        2. Diseño
        3. Implementación
        4. Validación
        5. Documentación
        """
    )

    # -- Lista de artefactos ------------------------------------------
    artifacts_path = settings.artifacts_path
    
    # Si hay un proyecto activo, mostrar su carpeta específica
    if st.session_state.project_name:
        project_path = artifacts_path / st.session_state.project_name
        if project_path.exists():
            files = sorted(
                str(f.relative_to(project_path)).replace("\\", "/")
                for f in project_path.rglob("*")
                if f.is_file() and f.name != ".gitkeep"
            )
            if files:
                st.divider()
                st.subheader(f"Archivos ({len(files)})")
                for fname in files[:10]:  # Mostrar solo primeros 10
                    st.text(f"  {fname}")
                if len(files) > 10:
                    st.caption(f"... y {len(files) - 10} más")
    else:
        # Mostrar todos los proyectos disponibles
        if artifacts_path.exists():
            projects = sorted(
                d.name for d in artifacts_path.iterdir() 
                if d.is_dir() and not d.name.startswith(".")
            )
            if projects:
                st.divider()
                st.subheader(f"Proyectos ({len(projects)})")
                for proj in projects:
                    st.text(f"  • {proj}")

    # -- Conocimiento aprendido ---------------------------------------
    if st.session_state.knowledge is not None:
        st.divider()
        st.subheader("Conocimiento del sistema")
        try:
            kstats = st.session_state.knowledge.get_knowledge_stats()
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Insights activos", kstats.get("total_active", 0))
            with col2:
                st.metric("Archivados", kstats.get("total_archived", 0))

            by_cat = kstats.get("by_category", [])
            if by_cat:
                with st.expander("Por categoría", expanded=False):
                    for c in by_cat[:10]:
                        st.text(
                            f"  {c['category']}: {c['count']} "
                            f"(score {c['avg_score']})"
                        )

            top = kstats.get("top_insights", [])
            if top:
                with st.expander("Top insights", expanded=False):
                    for t in top[:5]:
                        st.caption(
                            f"★ {t['score']} · {t['title'][:60]} "
                            f"(×{t['reinforcement']})"
                        )
        except Exception as _se:
            st.caption("No se pudieron cargar estadísticas")

# ── Verificacion de proveedor ───────────────────────────────────────


def _provider_ready(selected_provider: str) -> bool:
    if selected_provider == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if selected_provider == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if selected_provider == "google":
        return bool(os.environ.get("GOOGLE_API_KEY"))
    if selected_provider == "groq":
        return bool(os.environ.get("GROQ_API_KEY"))
    if selected_provider == "ollama":
        return True
    return False


_provider_is_ready = _provider_ready(provider)

# ── Area de contenido principal ─────────────────────────────────────

st.title("DevTeam AI")
st.markdown("Sistema automatizado de desarrollo de software")
st.divider()

if not _provider_is_ready:
    st.warning("Configura la API key en el archivo `.env`")
    st.stop()

# ── Mensaje de bienvenida inicial ───────────────────────────────────

if not st.session_state.messages:
    welcome = (
        "**Bienvenido a DevTeam AI**\n\n"
        "Este sistema convierte tu idea en software funcional de forma automática.\n\n"
        "**Proceso:**\n"
        "1. Describes tu proyecto\n"
        "2. El sistema hace preguntas para entender los detalles\n"
        "3. Se genera automáticamente todo el código necesario\n"
        "4. Recibes el software completo y listo para usar\n\n"
        "**Para comenzar, describe qué tipo de software necesitas.**"
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome})

# ── Historial de chat ───────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── Entrada de chat y procesamiento ─────────────────────────────────

if prompt := st.chat_input("Escribe tu idea o responde..."):
    # Mostrar mensaje del usuario inmediatamente
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Procesar con el equipo de desarrollo
    with st.chat_message("assistant"):
        # Crear contenedores para progreso
        progress_container = st.empty()
        status_container = st.empty()
        response_container = st.empty()
        
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
                        session_id=st.session_state.session_id,
                        project_name=st.session_state.project_name,
                    )

                team = st.session_state.team

                # Construir historial completo como List[Message]
                messages: list[Message] = []
                for msg in st.session_state.messages:
                    if msg["role"] == "assistant" and msg is st.session_state.messages[0]:
                        continue
                    messages.append(
                        Message(role=msg["role"], content=msg["content"])
                    )
                
                # Buscar contexto relevante en memoria vectorizada SOLO si es útil
                memory = st.session_state.memory
                context_info = ""
                
                search_keywords = ["similar", "como antes", "parecido", "igual que", "anterior", 
                                 "proyecto anterior", "ya hice", "reutilizar", "basado en"]
                should_search = any(keyword in prompt.lower() for keyword in search_keywords)
                is_first_interaction = len(st.session_state.messages) <= 2
                
                if memory and memory.is_enabled() and (should_search or is_first_interaction):
                    try:
                        similar_context = memory.search_similar_context(
                            query=prompt,
                            session_id=None,
                            limit=2
                        )
                        
                        context_parts = []
                        
                        if similar_context["requirements"]:
                            high_similarity = [r for r in similar_context["requirements"] if r["similarity"] > 0.8]
                            if high_similarity:
                                context_parts.append("Requisitos similares:")
                                for req in high_similarity[:1]:
                                    context_parts.append(f"- {req['requirement_id']}: {req['content'][:100]}...")
                        
                        if similar_context["designs"]:
                            high_similarity = [d for d in similar_context["designs"] if d["similarity"] > 0.8]
                            if high_similarity:
                                context_parts.append("\nDiseños similares:")
                                for design in high_similarity[:1]:
                                    context_parts.append(f"- {design['component_name']}")
                        
                        if context_parts:
                            context_info = "\n\n---\nCONTEXTO:\n" + "\n".join(context_parts) + "\n---\n"
                    except Exception as e:
                        import logging
                        logging.warning(f"Error buscando en memoria: {e}")
                
                if context_info and messages:
                    last_user_msg = messages[-1]
                    if last_user_msg.role == "user":
                        last_user_msg.content += context_info

                # Mostrar barra de progreso inicial
                progress_bar = progress_container.progress(0)
                status_text = status_container.info("Procesando...")
                
                # Ejecutar el orquestador primero
                result = team.run(messages, user_id=st.session_state.user_id, session_id=st.session_state.session_id, stream=False)
                
                # Detectar si el orquestador quiere ejecutar el pipeline
                execute_match = None
                if result and result.content:
                    import re
                    execute_match = re.search(r'EJECUTAR_PIPELINE:([a-z0-9-]+)', result.content, re.IGNORECASE)
                
                # Si detectó el comando, ejecutar pipeline mejorado
                if execute_match:
                    project_name = execute_match.group(1).lower().strip()
                    st.session_state.project_name = project_name

                    # Contexto y conocimiento previo
                    full_context = "\n\n".join(
                        f"{m['role']}: {m['content']}"
                        for m in st.session_state.messages[-10:]
                    )

                    prior_knowledge = ""
                    prior_knowledge_ids: list[int] = []
                    if st.session_state.knowledge:
                        try:
                            relevant = st.session_state.knowledge.search_relevant_knowledge(
                                query=full_context[:300],
                                limit=6,
                                project_type=None,
                            )
                            if relevant:
                                knowledge_lines = [
                                    f"[{k['category']}] {k['title']}: {k['insight']}"
                                    for k in relevant
                                ]
                                prior_knowledge_ids = [k["id"] for k in relevant]
                                prior_knowledge = (
                                    "\n\nCONOCIMIENTO PREVIO RELEVANTE (aprendido "
                                    "de proyectos anteriores):\n"
                                    + "\n".join(knowledge_lines)
                                    + "\nAplica este conocimiento donde sea pertinente.\n"
                                )
                        except Exception as _ke:
                            logger.warning(f"Error recuperando conocimiento: {_ke}")

                    # Reporter que integra con Streamlit progress + status
                    class _StreamlitReporter:
                        def set_status(self, phase: str, message: str) -> None:
                            status_text.info(f"{phase}: {message}")

                        def set_progress(self, pct: int) -> None:
                            progress_bar.progress(min(max(pct, 0), 100))

                    # Agente de análisis con la configuración efectiva
                    analysis_agent = create_analysis_agent(settings)

                    # Ejecutar pipeline completo
                    pipeline_result = run_pipeline(
                        settings=settings,
                        project_name=project_name,
                        user_context=full_context,
                        prior_knowledge=prior_knowledge,
                        prior_knowledge_ids=prior_knowledge_ids,
                        analysis_agent=analysis_agent,
                        reporter=_StreamlitReporter(),
                        enable_code_validation=True,
                        max_implementation_retries=1,
                        learning_agent=st.session_state.learning_agent,
                    )

                    progress_bar.progress(100)
                    status_text.success("Pipeline completado")

                    # Construir respuesta visible al usuario
                    full_response = pipeline_result.render_user_summary()
                    result = type("obj", (object,), {"content": full_response})()

                    # Aprendizaje autónomo — basado en el resultado estructurado
                    if st.session_state.learning_agent:
                        try:
                            impl_summary = (
                                f"Archivos generados ({len(pipeline_result.files_generated)}): "
                                + ", ".join(pipeline_result.files_generated[:20])
                            )
                            ptype = (
                                pipeline_result.stack_profile.project_type
                                if pipeline_result.stack_profile
                                else "web"
                            )
                            saved_count = st.session_state.learning_agent.learn_from_project(
                                project_name=project_name,
                                project_type=ptype,
                                user_request=full_context[:600],
                                analysis_doc=pipeline_result.analysis_doc,
                                design_doc=pipeline_result.design_doc,
                                implementation_summary=impl_summary,
                                validation_result=pipeline_result.validation_report[:500],
                                extra_context=pipeline_result.documentation_summary[:300],
                            )
                            if saved_count > 0:
                                logger.info(
                                    f"Sistema aprendió {saved_count} insights de '{project_name}'"
                                )
                        except Exception as _le:
                            logger.error(f"Error en aprendizaje: {_le}")
                
                # Si no ejecutó pipeline, ya tiene el result del orquestador
                progress_bar.progress(100)
                if not execute_match:
                    status_text.success("Listo")
                
                # Detectar nombre del proyecto en la respuesta si aún no existe
                if result and result.content and not st.session_state.project_name:
                    import re
                    match = re.search(r'\*\*Nombre\*\*:\s*\[?([a-z0-9-]+)\]?', result.content, re.IGNORECASE)
                    if match:
                        project_name = match.group(1).lower().strip()
                        st.session_state.project_name = project_name
                
                # Almacenar en memoria vectorizada
                memory = st.session_state.memory
                if memory and memory.is_enabled():
                    memory.store_conversation_message(
                        session_id=st.session_state.session_id,
                        role="user",
                        content=prompt
                    )
                    
                    if result and result.content:
                        memory.store_conversation_message(
                            session_id=st.session_state.session_id,
                            role="assistant",
                            content=result.content
                        )
                        
                        response_lower = result.content.lower()
                        
                        if "requisitos funcionales" in response_lower or "rf-" in response_lower:
                            memory.store_requirements(
                                session_id=st.session_state.session_id,
                                requirements_doc=result.content
                            )
                        
                        if "arquitectura" in response_lower or "adr-" in response_lower:
                            memory.store_design_components(
                                session_id=st.session_state.session_id,
                                design_doc=result.content
                            )
                        
                        if st.session_state.artifact_monitor:
                            st.session_state.artifact_monitor.scan_and_store(
                                session_id=st.session_state.session_id
                            )

        except Exception as exc:
            progress_container.empty()
            status_container.empty()
            st.error(f"Error: {exc}")
            import traceback
            st.code(traceback.format_exc())
            st.stop()

        # Limpiar contenedores de progreso
        progress_container.empty()
        status_container.empty()
        
        # Mostrar la respuesta
        response_text = (
            result.content if result and result.content else "No se genero respuesta."
        )
        st.markdown(response_text)

        # Persistir en historial
        st.session_state.messages.append(
            {"role": "assistant", "content": response_text}
        )

        # Mostrar artefactos generados SOLO si el pipeline acaba de ejecutarse
        if execute_match and st.session_state.project_name:
            artifacts_path = settings.artifacts_path
            project_path = artifacts_path / st.session_state.project_name
            if project_path.exists():
                generated = sorted(
                    str(f.relative_to(project_path)).replace("\\", "/")
                    for f in project_path.rglob("*")
                    if f.is_file() and f.name != ".gitkeep"
                )
                if generated:
                    with st.expander(
                        f"📁 Archivos generados en {st.session_state.project_name}/ ({len(generated)})",
                        expanded=False,
                    ):
                        for fname in generated:
                            file_path = project_path / fname
                            lang = fname.rsplit(".", 1)[-1] if "." in fname else ""
                            st.markdown(f"**`{fname}`**")
                            try:
                                st.code(
                                    file_path.read_text(encoding="utf-8"),
                                    language=lang,
                                )
                            except Exception:
                                st.text("(no se pudo leer el archivo)")
