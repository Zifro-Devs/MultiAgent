"""Integración de Memoria Vectorizada con el Pipeline.

Este módulo conecta VectorMemory con el flujo de trabajo de los agentes,
almacenando automáticamente conversaciones, requisitos, diseños y código.
"""

from __future__ import annotations

import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.storage.vector_memory import VectorMemory
from src.config.settings import Settings

logger = logging.getLogger(__name__)


class MemoryIntegration:
    """Integra memoria vectorizada en el pipeline de desarrollo."""

    def __init__(self, settings: Settings, project_id: Optional[str] = None):
        """Inicializa la integración de memoria.
        
        Args:
            settings: Configuración de la aplicación
            project_id: ID del proyecto (usa session_id si no se especifica)
        """
        self.settings = settings
        self.project_id = project_id
        self.vector_memory: Optional[VectorMemory] = None
        
        # Inicializar solo si hay Supabase configurado
        if settings.supabase_db_url:
            try:
                self.vector_memory = VectorMemory(settings.supabase_db_url)
                logger.info("✅ Memoria vectorizada inicializada")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo inicializar memoria vectorizada: {e}")
                self.vector_memory = None
        else:
            logger.info("ℹ️ Memoria vectorizada desactivada (SQLite en uso)")

    def is_enabled(self) -> bool:
        """Verifica si la memoria vectorizada está habilitada."""
        return self.vector_memory is not None

    def store_conversation_message(
        self,
        session_id: str,
        role: str,
        content: str,
        message_id: Optional[int] = None
    ):
        """Almacena un mensaje de conversación con embedding.
        
        Args:
            session_id: ID de la sesión
            role: Rol del mensaje (user/assistant)
            content: Contenido del mensaje
            message_id: ID del mensaje en la DB
        """
        if not self.is_enabled():
            return
        
        try:
            # Solo almacenar mensajes con contenido significativo
            if len(content.strip()) < 10:
                return
            
            metadata = {
                "role": role,
                "timestamp": datetime.now().isoformat(),
                "project_id": self.project_id or session_id,
            }
            
            self.vector_memory.store_conversation(
                session_id=session_id,
                content=content,
                message_id=message_id,
                metadata=metadata
            )
            
            logger.debug(f"💾 Conversación almacenada: {session_id} ({role})")
            
        except Exception as e:
            logger.error(f"Error almacenando conversación: {e}")

    def store_requirements(self, session_id: str, requirements_doc: str):
        """Extrae y almacena requisitos del documento de análisis.
        
        Args:
            session_id: ID de la sesión
            requirements_doc: Documento completo de requisitos
        """
        if not self.is_enabled():
            return
        
        try:
            project_id = self.project_id or session_id
            
            # Extraer requisitos funcionales (RF-XXX)
            rf_pattern = r'(RF-\d+)[:\s]+([^\n]+)'
            functional_reqs = re.findall(rf_pattern, requirements_doc, re.IGNORECASE)
            
            for req_id, req_text in functional_reqs:
                self.vector_memory.store_requirement(
                    project_id=project_id,
                    requirement_id=req_id,
                    content=req_text.strip(),
                    requirement_type="functional",
                    metadata={
                        "session_id": session_id,
                        "extracted_at": datetime.now().isoformat(),
                    }
                )
            
            # Extraer requisitos no funcionales (RNF-XXX)
            rnf_pattern = r'(RNF-\d+)[:\s]+([^\n]+)'
            non_functional_reqs = re.findall(rnf_pattern, requirements_doc, re.IGNORECASE)
            
            for req_id, req_text in non_functional_reqs:
                self.vector_memory.store_requirement(
                    project_id=project_id,
                    requirement_id=req_id,
                    content=req_text.strip(),
                    requirement_type="non_functional",
                    metadata={
                        "session_id": session_id,
                        "extracted_at": datetime.now().isoformat(),
                    }
                )
            
            # Extraer historias de usuario (HU-XXX)
            hu_pattern = r'(HU-\d+)[:\s]+([^\n]+(?:\n(?!##)[^\n]+)*)'
            user_stories = re.findall(hu_pattern, requirements_doc, re.IGNORECASE)
            
            for story_id, story_text in user_stories:
                self.vector_memory.store_requirement(
                    project_id=project_id,
                    requirement_id=story_id,
                    content=story_text.strip(),
                    requirement_type="user_story",
                    metadata={
                        "session_id": session_id,
                        "extracted_at": datetime.now().isoformat(),
                    }
                )
            
            total = len(functional_reqs) + len(non_functional_reqs) + len(user_stories)
            logger.info(f"✅ Requisitos almacenados: {total} (RF: {len(functional_reqs)}, RNF: {len(non_functional_reqs)}, HU: {len(user_stories)})")
            
        except Exception as e:
            logger.error(f"Error almacenando requisitos: {e}")

    def store_design_components(self, session_id: str, design_doc: str):
        """Extrae y almacena componentes de diseño.
        
        Args:
            session_id: ID de la sesión
            design_doc: Documento completo de diseño
        """
        if not self.is_enabled():
            return
        
        try:
            project_id = self.project_id or session_id
            
            # Extraer componentes (secciones ### 3.X)
            component_pattern = r'###\s+\d+\.\d+\s+([^\n]+)\n((?:(?!###).*\n?)*)'
            components = re.findall(component_pattern, design_doc)
            
            for comp_name, comp_content in components:
                if len(comp_content.strip()) > 20:
                    self.vector_memory.store_design(
                        project_id=project_id,
                        component_name=comp_name.strip(),
                        content=comp_content.strip(),
                        design_type="component",
                        metadata={
                            "session_id": session_id,
                            "extracted_at": datetime.now().isoformat(),
                        }
                    )
            
            # Extraer ADRs (Registros de Decisiones de Arquitectura)
            adr_pattern = r'###\s+(ADR-\d+)[:\s]+([^\n]+)\n((?:(?!###).*\n?)*)'
            adrs = re.findall(adr_pattern, design_doc)
            
            for adr_id, adr_title, adr_content in adrs:
                self.vector_memory.store_design(
                    project_id=project_id,
                    component_name=f"{adr_id}: {adr_title}",
                    content=adr_content.strip(),
                    design_type="architecture",
                    metadata={
                        "session_id": session_id,
                        "adr_id": adr_id,
                        "extracted_at": datetime.now().isoformat(),
                    }
                )
            
            total = len(components) + len(adrs)
            logger.info(f"✅ Componentes de diseño almacenados: {total} (Componentes: {len(components)}, ADRs: {len(adrs)})")
            
        except Exception as e:
            logger.error(f"Error almacenando diseño: {e}")

    def store_code_artifact(
        self,
        session_id: str,
        file_path: str,
        content: str,
        code_type: str = "module"
    ):
        """Almacena un artefacto de código con embedding.
        
        Args:
            session_id: ID de la sesión
            file_path: Ruta del archivo
            content: Contenido del código
            code_type: Tipo de código (module, function, class)
        """
        if not self.is_enabled():
            return
        
        try:
            project_id = self.project_id or session_id
            
            # Solo almacenar archivos de código (no configs ni docs)
            code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.cs'}
            file_ext = '.' + file_path.rsplit('.', 1)[-1] if '.' in file_path else ''
            
            if file_ext not in code_extensions:
                return
            
            # Limitar tamaño para embeddings
            if len(content) > 10000:
                # Tomar solo las primeras 10k caracteres
                content = content[:10000] + "\n... (truncado)"
            
            self.vector_memory.store_code(
                project_id=project_id,
                file_path=file_path,
                content=content,
                code_type=code_type,
                metadata={
                    "session_id": session_id,
                    "file_extension": file_ext,
                    "stored_at": datetime.now().isoformat(),
                }
            )
            
            logger.debug(f"💾 Código almacenado: {file_path}")
            
        except Exception as e:
            logger.error(f"Error almacenando código: {e}")

    def search_similar_context(
        self,
        query: str,
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Busca contexto similar en todas las categorías.
        
        Args:
            query: Texto de búsqueda
            session_id: Filtrar por sesión (opcional)
            limit: Número de resultados por categoría
            
        Returns:
            Diccionario con resultados por categoría
        """
        if not self.is_enabled():
            return {
                "conversations": [],
                "requirements": [],
                "designs": [],
                "code": [],
            }
        
        try:
            project_id = self.project_id or session_id
            
            results = {
                "conversations": self.vector_memory.search_similar_conversations(
                    query, limit=limit, session_id=session_id
                ),
                "requirements": self.vector_memory.search_similar_requirements(
                    query, limit=limit, project_id=project_id
                ),
                "designs": self.vector_memory.search_similar_designs(
                    query, limit=limit, project_id=project_id
                ),
                "code": self.vector_memory.search_similar_code(
                    query, limit=limit, project_id=project_id
                ),
            }
            
            total = sum(len(v) for v in results.values())
            logger.info(f"🔍 Búsqueda completada: {total} resultados encontrados")
            
            return results
            
        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {e}")
            return {
                "conversations": [],
                "requirements": [],
                "designs": [],
                "code": [],
            }

    def get_relevant_context_for_phase(
        self,
        phase: str,
        current_input: str,
        session_id: Optional[str] = None
    ) -> str:
        """Obtiene contexto relevante para una fase específica del pipeline.
        
        Args:
            phase: Fase actual (analysis, design, implementation, validation)
            current_input: Input actual del usuario
            session_id: ID de la sesión
            
        Returns:
            Contexto relevante formateado como string
        """
        if not self.is_enabled():
            return ""
        
        try:
            results = self.search_similar_context(
                query=current_input,
                session_id=session_id,
                limit=3
            )
            
            context_parts = []
            
            # Contexto según la fase
            if phase == "analysis":
                # En análisis, buscar requisitos similares de proyectos anteriores
                if results["requirements"]:
                    context_parts.append("## 📋 Requisitos Similares de Proyectos Anteriores\n")
                    for req in results["requirements"][:2]:
                        context_parts.append(f"- **{req['requirement_id']}** ({req['requirement_type']}): {req['content'][:200]}...")
            
            elif phase == "design":
                # En diseño, buscar arquitecturas similares
                if results["designs"]:
                    context_parts.append("## 🏗️ Diseños Similares de Proyectos Anteriores\n")
                    for design in results["designs"][:2]:
                        context_parts.append(f"- **{design['component_name']}**: {design['content'][:200]}...")
            
            elif phase == "implementation":
                # En implementación, buscar código similar
                if results["code"]:
                    context_parts.append("## 💻 Código Similar de Proyectos Anteriores\n")
                    for code in results["code"][:2]:
                        context_parts.append(f"- **{code['file_path']}**: {code['content'][:200]}...")
            
            elif phase == "validation":
                # En validación, buscar todo el contexto
                if results["requirements"]:
                    context_parts.append("## 📋 Requisitos del Proyecto\n")
                    for req in results["requirements"][:3]:
                        context_parts.append(f"- {req['requirement_id']}: {req['content'][:150]}...")
            
            return "\n".join(context_parts) if context_parts else ""
            
        except Exception as e:
            logger.error(f"Error obteniendo contexto relevante: {e}")
            return ""

    def close(self):
        """Cierra las conexiones de memoria."""
        if self.vector_memory:
            self.vector_memory.close()
