"""Página de Gestión de Sesiones.

Permite ver, continuar y eliminar sesiones anteriores.
"""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime

# Asegurar que el root del proyecto esté en sys.path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv()

import streamlit as st
from src.config.settings import get_settings
from src.storage.database import get_database
from src.storage.session_manager import SessionManager

# Configuración de página
st.set_page_config(
    page_title="Sesiones - DevTeam AI",
    page_icon="⚡",
    layout="wide",
)

# Inicializar
settings = get_settings()
db = get_database(settings)
session_mgr = SessionManager(db)

# Título
st.title("Gestión de Sesiones")
st.markdown("Administra tus conversaciones y proyectos anteriores.")
st.divider()

# Tabs
tab1, tab2, tab3 = st.tabs(["Explorar Sesiones", "Estadísticas", "Configuración"])

# ── TAB 1: Explorar Sesiones ────────────────────────────────────────

with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("Sesiones Activas")
    
    with col2:
        if st.button("Actualizar", use_container_width=True):
            st.rerun()
    
    # Filtros
    col_filter1, col_filter2 = st.columns(2)
    
    with col_filter1:
        filter_user = st.text_input("Filtrar por usuario", placeholder="Dejar vacío para ver todas")
    
    with col_filter2:
        limit = st.number_input("Número de sesiones", min_value=10, max_value=200, value=50, step=10)
    
    # Obtener sesiones
    with st.spinner("Cargando sesiones..."):
        sessions = session_mgr.get_active_sessions(
            user_id=filter_user if filter_user else None,
            limit=limit
        )
    
    if not sessions:
        st.info("No hay sesiones guardadas todavía. ¡Comienza una nueva conversación!")
    else:
        st.success(f"{len(sessions)} sesiones encontradas")
        
        # Mostrar sesiones
        for idx, session in enumerate(sessions):
            with st.expander(
                f"Sesión {idx + 1}: {session['session_id'][:12]}... "
                f"({session['message_count']} mensajes)",
                expanded=False
            ):
                col_info1, col_info2, col_info3 = st.columns(3)
                
                with col_info1:
                    st.metric("Usuario", session['user_id'])
                    st.caption(f"**Creada:** {session['created_at']}")
                
                with col_info2:
                    st.metric("Mensajes", session['message_count'])
                    st.metric("Ejecuciones", session['run_count'])
                
                with col_info3:
                    if session['last_message_at']:
                        st.caption(f"**Última actividad:**")
                        st.caption(f"{session['last_message_at']}")
                
                st.divider()
                
                # Acciones
                col_action1, col_action2, col_action3, col_action4 = st.columns(4)
                
                with col_action1:
                    if st.button("📖 Ver Mensajes", key=f"view_{session['session_id']}", use_container_width=True):
                        st.session_state['viewing_session'] = session['session_id']
                
                with col_action2:
                    if st.button("Continuar", key=f"continue_{session['session_id']}", use_container_width=True):
                        # Cargar sesión en la app principal
                        st.session_state.session_id = session['session_id']
                        st.session_state.user_id = session['user_id']
                        st.session_state.team = None  # Forzar recarga del equipo
                        
                        # Cargar mensajes
                        messages = session_mgr.get_session_messages(session['session_id'])
                        st.session_state.messages = [
                            {"role": msg["role"], "content": msg["content"]}
                            for msg in messages
                        ]
                        
                        st.success(f"Sesión cargada: {session['session_id'][:12]}...")
                        st.info("Ve a la página principal para continuar la conversación")
                
                with col_action3:
                    if st.button("📥 Exportar", key=f"export_{session['session_id']}", use_container_width=True):
                        # Obtener mensajes
                        messages = session_mgr.get_session_messages(session['session_id'])
                        
                        # Formatear como texto
                        export_text = f"# Sesión: {session['session_id']}\n"
                        export_text += f"Usuario: {session['user_id']}\n"
                        export_text += f"Creada: {session['created_at']}\n"
                        export_text += f"Mensajes: {len(messages)}\n\n"
                        export_text += "=" * 80 + "\n\n"
                        
                        for msg in messages:
                            export_text += f"## {msg['role'].upper()}\n"
                            export_text += f"{msg['content']}\n\n"
                            export_text += "-" * 80 + "\n\n"
                        
                        st.download_button(
                            label="Descargar TXT",
                            data=export_text,
                            file_name=f"session_{session['session_id'][:8]}.txt",
                            mime="text/plain",
                            key=f"download_{session['session_id']}",
                            use_container_width=True
                        )
                
                with col_action4:
                    if st.button("Eliminar", key=f"delete_{session['session_id']}", type="secondary", use_container_width=True):
                        st.session_state[f'confirm_delete_{session["session_id"]}'] = True
                
                # Confirmación de eliminación
                if st.session_state.get(f'confirm_delete_{session["session_id"]}', False):
                    st.warning("¿Estás seguro? Esta acción no se puede deshacer.")
                    col_confirm1, col_confirm2 = st.columns(2)
                    
                    with col_confirm1:
                        if st.button("Sí, eliminar", key=f"confirm_yes_{session['session_id']}", use_container_width=True):
                            if session_mgr.delete_session(session['session_id']):
                                st.success("Sesión eliminada correctamente")
                                del st.session_state[f'confirm_delete_{session["session_id"]}']
                                st.rerun()
                            else:
                                st.error("Error al eliminar la sesión")
                    
                    with col_confirm2:
                        if st.button("Cancelar", key=f"confirm_no_{session['session_id']}", use_container_width=True):
                            del st.session_state[f'confirm_delete_{session["session_id"]}']
                            st.rerun()
                
                # Mostrar mensajes si se solicitó
                if st.session_state.get('viewing_session') == session['session_id']:
                    st.markdown("### Historial de Mensajes")
                    
                    messages = session_mgr.get_session_messages(session['session_id'])
                    
                    if messages:
                        for msg in messages:
                            with st.chat_message(msg['role']):
                                st.markdown(msg['content'])
                                st.caption(f"_{msg['created_at']}_")
                    else:
                        st.info("No hay mensajes en esta sesión")
                    
                    if st.button("Cerrar", key=f"close_view_{session['session_id']}"):
                        del st.session_state['viewing_session']
                        st.rerun()

# ── TAB 2: Estadísticas ─────────────────────────────────────────────

with tab2:
    st.subheader("Estadísticas Generales")
    
    with st.spinner("Calculando estadísticas..."):
        all_sessions = session_mgr.get_active_sessions(limit=1000)
    
    if all_sessions:
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        
        with col_stat1:
            st.metric("Total de Sesiones", len(all_sessions))
        
        with col_stat2:
            total_messages = sum(s['message_count'] for s in all_sessions)
            st.metric("Total de Mensajes", total_messages)
        
        with col_stat3:
            total_runs = sum(s['run_count'] for s in all_sessions)
            st.metric("Total de Ejecuciones", total_runs)
        
        with col_stat4:
            unique_users = len(set(s['user_id'] for s in all_sessions))
            st.metric("Usuarios Únicos", unique_users)
        
        st.divider()
        
        # Gráfico de actividad
        st.subheader("Actividad Reciente")
        
        # Preparar datos para gráfico
        import pandas as pd
        
        df = pd.DataFrame(all_sessions)
        df['created_at'] = pd.to_datetime(df['created_at'])
        df['date'] = df['created_at'].dt.date
        
        activity = df.groupby('date').size().reset_index(name='sesiones')
        
        st.line_chart(activity.set_index('date'))
        
        # Top usuarios
        st.subheader("👥 Usuarios Más Activos")
        
        user_activity = df.groupby('user_id').agg({
            'session_id': 'count',
            'message_count': 'sum',
            'run_count': 'sum'
        }).reset_index()
        
        user_activity.columns = ['Usuario', 'Sesiones', 'Mensajes', 'Ejecuciones']
        user_activity = user_activity.sort_values('Mensajes', ascending=False).head(10)
        
        st.dataframe(user_activity, use_container_width=True, hide_index=True)
    
    else:
        st.info("No hay datos suficientes para mostrar estadísticas")

# ── TAB 3: Configuración ────────────────────────────────────────────

with tab3:
    st.subheader("Configuración de Sesiones")
    
    st.markdown("""
    ### Base de Datos Actual
    """)
    
    if settings.supabase_db_url:
        st.success("PostgreSQL (Supabase) - Producción")
        st.caption("Memoria persistente con soporte para múltiples usuarios")
    else:
        st.info("SQLite Local - Desarrollo")
        st.caption(f"Base de datos: `{settings.project_root / 'data' / 'devteam.db'}`")
    
    st.divider()
    
    st.markdown("""
    ### Memoria Vectorizada
    """)
    
    if settings.supabase_db_url:
        st.success("Habilitada - Búsqueda semántica activa")
        st.caption("Permite encontrar proyectos y conversaciones similares")
        
        # Verificar si las tablas existen
        try:
            from src.storage.vector_memory import VectorMemory
            vm = VectorMemory(settings.supabase_db_url)
            
            if st.button("Crear/Verificar Tablas Vectorizadas"):
                with st.spinner("Creando tablas..."):
                    vm.create_tables()
                    st.success("Tablas vectorizadas verificadas/creadas")
            
            vm.close()
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.warning("Deshabilitada - Requiere PostgreSQL")
        st.caption("La memoria vectorizada solo funciona con Supabase/PostgreSQL")
    
    st.divider()
    
    st.markdown("""
    ### Mantenimiento
    """)
    
    col_maint1, col_maint2 = st.columns(2)
    
    with col_maint1:
        if st.button("Limpiar Sesiones Antiguas", use_container_width=True):
            st.info("Función en desarrollo")
    
    with col_maint2:
        if st.button("Exportar Todas las Sesiones", use_container_width=True):
            st.info("Función en desarrollo")
    
    st.divider()
    
    st.markdown("""
    ### Información del Sistema
    """)
    
    st.code(f"""
Provider: {settings.llm_provider}
Modelo: {settings.llm_model}
Orquestador: {settings.orchestrator_model}
Artifacts: {settings.artifacts_dir}
Debug: {settings.debug}
    """)
