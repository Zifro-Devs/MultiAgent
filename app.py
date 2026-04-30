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
from src.storage.memory_integration import MemoryIntegration  # noqa: E402
from src.storage.database import get_database  # noqa: E402
from src.storage.session_manager import SessionManager  # noqa: E402
from src.storage.artifact_monitor import ArtifactMonitor  # noqa: E402
from src.storage.knowledge_memory import KnowledgeMemory  # noqa: E402
from src.agents.learning import LearningAgent  # noqa: E402
from src.agents.documentation import create_documentation_agent  # noqa: E402

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
                
                # Si detectó el comando, ejecutar pipeline automáticamente
                if execute_match:
                    project_name = execute_match.group(1).lower().strip()
                    st.session_state.project_name = project_name
                    
                    status_text.info("Ejecutando...")
                    
                    # Recrear team con proyecto
                    st.session_state.team = create_dev_team(
                        overrides={
                            "llm_provider": provider,
                            "llm_model": model_id,
                            "orchestrator_model": orch_model,
                            "ollama_host": ollama_host,
                        },
                        session_id=st.session_state.session_id,
                        project_name=project_name,
                    )
                    team = st.session_state.team
                    
                    # Contexto completo
                    full_context = "\n\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages[-10:]])
                    full_response = f"**{project_name}**\n\n"
                    
                    # Recuperar conocimiento previo relevante para este proyecto
                    prior_knowledge = ""
                    if st.session_state.knowledge:
                        try:
                            relevant = st.session_state.knowledge.search_relevant_knowledge(
                                query=full_context[:300],
                                limit=6,
                            )
                            if relevant:
                                knowledge_lines = []
                                for k in relevant:
                                    knowledge_lines.append(
                                        f"[{k['category']}] {k['title']}: {k['insight']}"
                                    )
                                prior_knowledge = (
                                    "\n\nCONOCIMIENTO PREVIO RELEVANTE (aprendido de proyectos anteriores):\n"
                                    + "\n".join(knowledge_lines)
                                    + "\nAplica este conocimiento donde sea pertinente.\n"
                                )
                        except Exception as _ke:
                            logger.warning(f"Error recuperando conocimiento: {_ke}")

                    # 1. ANÁLISIS - Pasar TODO el contexto
                    progress_bar.progress(10)
                    status_text.info("Fase 1/4: Análisis")
                    analysis_prompt = f"""Genera especificación IEEE 830 COMPLETA basada en esta conversación:

{full_context}
{prior_knowledge}
IMPORTANTE:
- Incluye TODOS los requisitos funcionales mencionados
- Agrega requisitos no funcionales (rendimiento, seguridad, escalabilidad)
- Define historias de usuario detalladas
- Especifica casos de uso con flujos completos
- Define modelo de datos conceptual
"""
                    analysis_result = team.members[0].run(analysis_prompt)
                    full_response += f"1. Análisis completado\n"
                    progress_bar.progress(25)
                    
                    # 2. DISEÑO - Pasar requisitos COMPLETOS
                    status_text.info("Fase 2/4: Diseño")
                    design_prompt = f"""Diseña arquitectura COMPLETA basada en estos requisitos:

{analysis_result.content}

DEBES INCLUIR:
- Arquitectura de componentes (frontend, backend, BD)
- Diseño de base de datos (tablas, relaciones, índices, SQL)
- APIs REST completas (todos los endpoints con request/response)
- Stack tecnológico justificado
- Diagramas de arquitectura
- Decisiones de diseño (ADRs)
"""
                    design_result = team.members[1].run(design_prompt)
                    full_response += f"2. Diseño completado\n"
                    progress_bar.progress(50)
                    
                    # 3. IMPLEMENTACIÓN
                    status_text.info("Fase 3/5: Implementación")
                    impl_prompt = f"""Implementa el sistema completo basado en este diseño:

{design_result.content}

EXIGENCIAS:
- Implementa CADA módulo, CADA endpoint, CADA vista definida en el diseño — sin excepción
- Nada de "// TODO", nada de stubs, nada de placeholders — código real que funciona
- La BD se conecta exclusivamente via variables de entorno. Genera el script SQL completo \
con tablas, relaciones, índices, constraints y datos seed para arrancar
- El .env.example debe tener TODAS las variables documentadas — el usuario solo pone sus \
credenciales y el sistema arranca sin tocar código
- Frontend: implementa TODAS las páginas con sus estados de carga, error y vacío
- El sistema debe ser indistinguible de uno hecho por un equipo de desarrollo profesional
"""
                    impl_result = team.members[2].run(impl_prompt)
                    full_response += f"3. Implementación completada\n"
                    progress_bar.progress(75)
                    
                    # 4. VALIDACIÓN
                    status_text.info("Fase 4/5: Validación")
                    val_prompt = f"""Valida el código generado:

DISEÑO:
{design_result.content[:1000]}

REVISA:
1. Seguridad OWASP Top 10
2. Calidad de código (SOLID, DRY)
3. Cobertura de requisitos
4. Tests funcionales
5. Genera tests adicionales si faltan

Genera informe de validación y tests faltantes.
"""
                    val_result = team.members[3].run(val_prompt)
                    full_response += f"4. Validación completada\n"
                    progress_bar.progress(80)

                    # 5. DOCUMENTACIÓN
                    status_text.info("Fase 5/5: Documentación")
                    try:
                        project_artifacts_dir = str(settings.artifacts_path / project_name)
                        doc_agent = create_documentation_agent(settings, artifacts_dir=project_artifacts_dir)
                        doc_prompt = f"""Genera la documentación completa del proyecto.

CONTEXTO DEL PROYECTO:
- Nombre: {project_name}
- Lo que pidió el usuario: {full_context[:400]}

ANÁLISIS (requisitos):
{analysis_result.content[:1200]}

DISEÑO (arquitectura y stack):
{design_result.content[:1200]}

VALIDACIÓN (estado del código):
{val_result.content[:600]}

Lee los archivos reales del proyecto con list_files() y read_file() \
para que la documentación sea 100% específica a lo que se generó. \
Luego escribe README.md y PROYECTO.md en la raíz del proyecto.
"""
                        doc_result = doc_agent.run(doc_prompt)
                        full_response += f"5. Documentación generada\n\n"
                    except Exception as _de:
                        logger.error(f"Error generando documentación: {_de}")
                        full_response += f"5. Documentación (error: {_de})\n\n"
                        doc_result = type('obj', (object,), {'content': ''})()

                    progress_bar.progress(100)
                    full_response += f"Proyecto completado en: `artifacts/{project_name}/`"
                    result = type('obj', (object,), {'content': full_response})()
                    status_text.success("Completado")

                    # ── APRENDIZAJE AUTÓNOMO ─────────────────────────────
                    # La IA analiza el proyecto y guarda lo que vale la pena recordar
                    if st.session_state.learning_agent:
                        try:
                            impl_files = []
                            project_path = settings.artifacts_path / project_name
                            if project_path.exists():
                                impl_files = [
                                    str(f.relative_to(project_path)).replace("\\", "/")
                                    for f in project_path.rglob("*") if f.is_file()
                                ]
                            impl_summary = f"Archivos generados ({len(impl_files)}): " + ", ".join(impl_files[:20])

                            # Detectar tipo de proyecto desde el contexto
                            ptype = "web"
                            ctx_lower = full_context.lower()
                            if "api" in ctx_lower or "rest" in ctx_lower:
                                ptype = "api"
                            elif "mobile" in ctx_lower or "móvil" in ctx_lower:
                                ptype = "mobile"
                            elif "cli" in ctx_lower or "terminal" in ctx_lower:
                                ptype = "cli"
                            elif "machine learning" in ctx_lower or " ml " in ctx_lower:
                                ptype = "ml"

                            saved_count = st.session_state.learning_agent.learn_from_project(
                                project_name=project_name,
                                project_type=ptype,
                                user_request=full_context[:600],
                                analysis_doc=analysis_result.content,
                                design_doc=design_result.content,
                                implementation_summary=impl_summary,
                                validation_result=val_result.content[:500],
                                extra_context=doc_result.content[:300] if doc_result and doc_result.content else None,
                            )
                            if saved_count > 0:
                                logger.info(f"Sistema aprendió {saved_count} insights de '{project_name}'")
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
