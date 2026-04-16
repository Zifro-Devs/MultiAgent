"""Página de Búsqueda Semántica.

Permite buscar en conversaciones, requisitos, diseños y código anteriores.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que el root del proyecto esté en sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from src.config.settings import get_settings
from src.storage.memory_integration import MemoryIntegration

# Configuración de página
st.set_page_config(
    page_title="Búsqueda Semántica - DevTeam AI",
    page_icon="🔍",
    layout="wide",
)

# Inicializar
settings = get_settings()
memory = MemoryIntegration(settings)

# Título
st.title("🔍 Búsqueda Semántica")
st.markdown("Encuentra proyectos, conversaciones y código similar usando IA.")
st.divider()

# Verificar si está habilitada
if not memory.is_enabled():
    st.warning("""
    ⚠️ **Búsqueda Semántica Deshabilitada**
    
    La búsqueda semántica requiere PostgreSQL (Supabase) con la extensión pgvector.
    
    **Para habilitarla:**
    1. Configura `SUPABASE_DB_URL` en tu archivo `.env`
    2. Ve a la página de **Sesiones** → **Configuración**
    3. Haz clic en "Crear/Verificar Tablas Vectorizadas"
    
    Actualmente estás usando SQLite, que no soporta búsqueda vectorial.
    """)
    st.stop()

# Interfaz de búsqueda
st.subheader("🎯 Buscar en tu Historial")

col_search1, col_search2 = st.columns([4, 1])

with col_search1:
    query = st.text_input(
        "¿Qué estás buscando?",
        placeholder="Ej: sistema de autenticación con JWT, API REST para usuarios, validación de formularios...",
        help="Describe lo que buscas en lenguaje natural"
    )

with col_search2:
    limit = st.number_input("Resultados", min_value=1, max_value=20, value=5)

# Filtros avanzados
with st.expander("🔧 Filtros Avanzados", expanded=False):
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        filter_session = st.text_input(
            "Filtrar por sesión (ID)",
            placeholder="Dejar vacío para buscar en todas",
            help="Buscar solo en una sesión específica"
        )
    
    with col_filter2:
        search_categories = st.multiselect(
            "Categorías",
            ["Conversaciones", "Requisitos", "Diseños", "Código"],
            default=["Conversaciones", "Requisitos", "Diseños", "Código"]
        )

# Botón de búsqueda
if st.button("🔍 Buscar", type="primary", use_container_width=True):
    if not query:
        st.warning("⚠️ Por favor ingresa un término de búsqueda")
    else:
        with st.spinner("🤖 Buscando con IA..."):
            results = memory.search_similar_context(
                query=query,
                session_id=filter_session if filter_session else None,
                limit=limit
            )
        
        # Mostrar resultados
        st.divider()
        st.subheader("📊 Resultados")
        
        total_results = sum(len(v) for v in results.values())
        
        if total_results == 0:
            st.info("📭 No se encontraron resultados. Intenta con otros términos de búsqueda.")
        else:
            st.success(f"✅ {total_results} resultados encontrados")
            
            # Tabs por categoría
            tabs = []
            tab_names = []
            
            if "Conversaciones" in search_categories and results["conversations"]:
                tab_names.append(f"💬 Conversaciones ({len(results['conversations'])})")
                tabs.append("conversations")
            
            if "Requisitos" in search_categories and results["requirements"]:
                tab_names.append(f"📋 Requisitos ({len(results['requirements'])})")
                tabs.append("requirements")
            
            if "Diseños" in search_categories and results["designs"]:
                tab_names.append(f"🏗️ Diseños ({len(results['designs'])})")
                tabs.append("designs")
            
            if "Código" in search_categories and results["code"]:
                tab_names.append(f"💻 Código ({len(results['code'])})")
                tabs.append("code")
            
            if not tabs:
                st.info("📭 No hay resultados en las categorías seleccionadas")
            else:
                tab_objects = st.tabs(tab_names)
                
                for tab_obj, tab_key in zip(tab_objects, tabs):
                    with tab_obj:
                        if tab_key == "conversations":
                            for idx, conv in enumerate(results["conversations"]):
                                with st.expander(
                                    f"💬 Conversación {idx + 1} - Similitud: {conv['similarity']:.2%}",
                                    expanded=idx == 0
                                ):
                                    st.markdown(f"**Sesión:** `{conv['session_id'][:12]}...`")
                                    st.caption(f"**Fecha:** {conv['created_at']}")
                                    st.divider()
                                    st.markdown(conv['content'])
                                    
                                    if conv.get('metadata'):
                                        st.caption(f"**Metadata:** {conv['metadata']}")
                        
                        elif tab_key == "requirements":
                            for idx, req in enumerate(results["requirements"]):
                                with st.expander(
                                    f"📋 {req['requirement_id']} - {req['requirement_type']} - Similitud: {req['similarity']:.2%}",
                                    expanded=idx == 0
                                ):
                                    st.markdown(f"**Proyecto:** `{req['project_id'][:12]}...`")
                                    st.caption(f"**Tipo:** {req['requirement_type']}")
                                    st.caption(f"**Fecha:** {req['created_at']}")
                                    st.divider()
                                    st.markdown(req['content'])
                        
                        elif tab_key == "designs":
                            for idx, design in enumerate(results["designs"]):
                                with st.expander(
                                    f"🏗️ {design['component_name']} - Similitud: {design['similarity']:.2%}",
                                    expanded=idx == 0
                                ):
                                    st.markdown(f"**Proyecto:** `{design['project_id'][:12]}...`")
                                    st.caption(f"**Tipo:** {design['design_type']}")
                                    st.caption(f"**Fecha:** {design['created_at']}")
                                    st.divider()
                                    st.markdown(design['content'])
                        
                        elif tab_key == "code":
                            for idx, code in enumerate(results["code"]):
                                with st.expander(
                                    f"💻 {code['file_path']} - Similitud: {code['similarity']:.2%}",
                                    expanded=idx == 0
                                ):
                                    st.markdown(f"**Proyecto:** `{code['project_id'][:12]}...`")
                                    st.caption(f"**Tipo:** {code['code_type']}")
                                    st.caption(f"**Fecha:** {code['created_at']}")
                                    st.divider()
                                    
                                    # Detectar lenguaje por extensión
                                    ext = code['file_path'].rsplit('.', 1)[-1] if '.' in code['file_path'] else ''
                                    st.code(code['content'], language=ext)

# Información adicional
st.divider()

with st.expander("ℹ️ ¿Cómo funciona la búsqueda semántica?", expanded=False):
    st.markdown("""
    ### 🧠 Búsqueda Inteligente con IA
    
    A diferencia de la búsqueda tradicional por palabras clave, la búsqueda semántica:
    
    - **Entiende el significado** de tu consulta, no solo las palabras exactas
    - **Encuentra contenido similar** aunque use términos diferentes
    - **Aprende de tus proyectos** anteriores para darte mejores resultados
    
    ### 🔬 Tecnología
    
    - **Embeddings:** Convierte texto en vectores numéricos de 384 dimensiones
    - **Modelo:** sentence-transformers (all-MiniLM-L6-v2)
    - **Base de datos:** PostgreSQL con extensión pgvector
    - **Índice:** HNSW (Hierarchical Navigable Small World) para búsqueda rápida
    
    ### 💡 Ejemplos de Búsqueda
    
    **Buscar por funcionalidad:**
    - "autenticación de usuarios"
    - "validación de formularios"
    - "integración con API externa"
    
    **Buscar por tecnología:**
    - "React con TypeScript"
    - "FastAPI con PostgreSQL"
    - "Docker compose para desarrollo"
    
    **Buscar por patrón:**
    - "arquitectura hexagonal"
    - "patrón repository"
    - "manejo de errores centralizado"
    """)

with st.expander("📊 Estadísticas de Memoria", expanded=False):
    st.markdown("""
    ### 📈 Estado de la Memoria Vectorizada
    
    🚧 **En desarrollo:** Panel de estadísticas
    
    Próximamente podrás ver:
    - Total de embeddings almacenados
    - Distribución por categoría
    - Proyectos indexados
    - Tamaño de la base de datos vectorial
    """)
