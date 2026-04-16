"""Sistema de Memoria Vectorizada con pgvector.

Permite búsqueda semántica de conversaciones, requisitos, diseños
y código generado anteriormente.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class VectorMemory:
    """Gestiona memoria vectorizada con embeddings para búsqueda semántica."""

    def __init__(self, db_url: str, embedding_model: str = "all-MiniLM-L6-v2"):
        """Inicializa el sistema de memoria vectorizada.
        
        Args:
            db_url: URL de conexión a PostgreSQL con pgvector
            embedding_model: Modelo de sentence-transformers para embeddings
        """
        self.db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        self.embedding_model_name = embedding_model
        self._encoder = None
        self._conn = None
        
    @property
    def encoder(self):
        """Lazy loading del modelo de embeddings."""
        if self._encoder is None:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Cargando modelo de embeddings: {self.embedding_model_name}")
            self._encoder = SentenceTransformer(self.embedding_model_name)
        return self._encoder
    
    def get_connection(self):
        """Obtiene conexión a PostgreSQL."""
        if self._conn is None or self._conn.closed:
            import psycopg
            self._conn = psycopg.connect(self.db_url)
        return self._conn
    
    def create_tables(self):
        """Crea las tablas necesarias para memoria vectorizada."""
        conn = self.get_connection()
        cur = conn.cursor()
        
        # Activar extensión pgvector
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        
        # Tabla de embeddings de conversaciones
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_embeddings (
                id SERIAL PRIMARY KEY,
                session_id TEXT NOT NULL,
                message_id INTEGER,
                content TEXT NOT NULL,
                embedding vector(384),  -- all-MiniLM-L6-v2 produce 384 dimensiones
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Tabla de embeddings de requisitos
        cur.execute("""
            CREATE TABLE IF NOT EXISTS requirement_embeddings (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                requirement_id TEXT NOT NULL,
                requirement_type TEXT,  -- 'functional', 'non_functional', 'user_story'
                content TEXT NOT NULL,
                embedding vector(384),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Tabla de embeddings de diseño
        cur.execute("""
            CREATE TABLE IF NOT EXISTS design_embeddings (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                component_name TEXT NOT NULL,
                design_type TEXT,  -- 'architecture', 'component', 'api', 'data_model'
                content TEXT NOT NULL,
                embedding vector(384),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Tabla de embeddings de código
        cur.execute("""
            CREATE TABLE IF NOT EXISTS code_embeddings (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                code_type TEXT,  -- 'function', 'class', 'module'
                content TEXT NOT NULL,
                embedding vector(384),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Índices para búsqueda vectorial eficiente (HNSW)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS conversation_embeddings_idx 
            ON conversation_embeddings 
            USING hnsw (embedding vector_cosine_ops);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS requirement_embeddings_idx 
            ON requirement_embeddings 
            USING hnsw (embedding vector_cosine_ops);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS design_embeddings_idx 
            ON design_embeddings 
            USING hnsw (embedding vector_cosine_ops);
        """)
        
        cur.execute("""
            CREATE INDEX IF NOT EXISTS code_embeddings_idx 
            ON code_embeddings 
            USING hnsw (embedding vector_cosine_ops);
        """)
        
        conn.commit()
        cur.close()
        logger.info("✅ Tablas de memoria vectorizada creadas")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Genera embedding para un texto.
        
        Args:
            text: Texto a convertir en embedding
            
        Returns:
            Vector numpy con el embedding
        """
        return self.encoder.encode(text, convert_to_numpy=True)
    
    def store_conversation(
        self,
        session_id: str,
        content: str,
        message_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena una conversación con su embedding.
        
        Args:
            session_id: ID de la sesión
            content: Contenido del mensaje
            message_id: ID del mensaje (opcional)
            metadata: Metadata adicional (opcional)
        """
        embedding = self.generate_embedding(content)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO conversation_embeddings 
            (session_id, message_id, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (session_id, message_id, content, embedding.tolist(), metadata))
        
        conn.commit()
        cur.close()
        logger.debug(f"Conversación almacenada: session={session_id}")
    
    def store_requirement(
        self,
        project_id: str,
        requirement_id: str,
        content: str,
        requirement_type: str = "functional",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena un requisito con su embedding."""
        embedding = self.generate_embedding(content)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO requirement_embeddings 
            (project_id, requirement_id, requirement_type, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (project_id, requirement_id, requirement_type, content, embedding.tolist(), metadata))
        
        conn.commit()
        cur.close()
        logger.debug(f"Requisito almacenado: {requirement_id}")
    
    def store_design(
        self,
        project_id: str,
        component_name: str,
        content: str,
        design_type: str = "component",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena un componente de diseño con su embedding."""
        embedding = self.generate_embedding(content)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO design_embeddings 
            (project_id, component_name, design_type, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (project_id, component_name, design_type, content, embedding.tolist(), metadata))
        
        conn.commit()
        cur.close()
        logger.debug(f"Diseño almacenado: {component_name}")
    
    def store_code(
        self,
        project_id: str,
        file_path: str,
        content: str,
        code_type: str = "module",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Almacena código con su embedding."""
        embedding = self.generate_embedding(content)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        cur.execute("""
            INSERT INTO code_embeddings 
            (project_id, file_path, code_type, content, embedding, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (project_id, file_path, code_type, content, embedding.tolist(), metadata))
        
        conn.commit()
        cur.close()
        logger.debug(f"Código almacenado: {file_path}")
    
    def search_similar_conversations(
        self,
        query: str,
        limit: int = 5,
        session_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca conversaciones similares usando búsqueda semántica.
        
        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados
            session_id: Filtrar por sesión específica (opcional)
            
        Returns:
            Lista de conversaciones similares con scores
        """
        query_embedding = self.generate_embedding(query)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT 
                id, session_id, content, metadata, created_at,
                1 - (embedding <=> %s::vector) as similarity
            FROM conversation_embeddings
        """
        params = [query_embedding.tolist()]
        
        if session_id:
            sql += " WHERE session_id = %s"
            params.append(session_id)
        
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding.tolist(), limit])
        
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "content": r[2],
                "metadata": r[3],
                "created_at": r[4],
                "similarity": float(r[5])
            }
            for r in results
        ]
    
    def search_similar_requirements(
        self,
        query: str,
        limit: int = 5,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca requisitos similares."""
        query_embedding = self.generate_embedding(query)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT 
                id, project_id, requirement_id, requirement_type, 
                content, metadata, created_at,
                1 - (embedding <=> %s::vector) as similarity
            FROM requirement_embeddings
        """
        params = [query_embedding.tolist()]
        
        if project_id:
            sql += " WHERE project_id = %s"
            params.append(project_id)
        
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding.tolist(), limit])
        
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        
        return [
            {
                "id": r[0],
                "project_id": r[1],
                "requirement_id": r[2],
                "requirement_type": r[3],
                "content": r[4],
                "metadata": r[5],
                "created_at": r[6],
                "similarity": float(r[7])
            }
            for r in results
        ]
    
    def search_similar_designs(
        self,
        query: str,
        limit: int = 5,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca diseños similares."""
        query_embedding = self.generate_embedding(query)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT 
                id, project_id, component_name, design_type,
                content, metadata, created_at,
                1 - (embedding <=> %s::vector) as similarity
            FROM design_embeddings
        """
        params = [query_embedding.tolist()]
        
        if project_id:
            sql += " WHERE project_id = %s"
            params.append(project_id)
        
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding.tolist(), limit])
        
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        
        return [
            {
                "id": r[0],
                "project_id": r[1],
                "component_name": r[2],
                "design_type": r[3],
                "content": r[4],
                "metadata": r[5],
                "created_at": r[6],
                "similarity": float(r[7])
            }
            for r in results
        ]
    
    def search_similar_code(
        self,
        query: str,
        limit: int = 5,
        project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Busca código similar."""
        query_embedding = self.generate_embedding(query)
        
        conn = self.get_connection()
        cur = conn.cursor()
        
        sql = """
            SELECT 
                id, project_id, file_path, code_type,
                content, metadata, created_at,
                1 - (embedding <=> %s::vector) as similarity
            FROM code_embeddings
        """
        params = [query_embedding.tolist()]
        
        if project_id:
            sql += " WHERE project_id = %s"
            params.append(project_id)
        
        sql += " ORDER BY embedding <=> %s::vector LIMIT %s"
        params.extend([query_embedding.tolist(), limit])
        
        cur.execute(sql, params)
        results = cur.fetchall()
        cur.close()
        
        return [
            {
                "id": r[0],
                "project_id": r[1],
                "file_path": r[2],
                "code_type": r[3],
                "content": r[4],
                "metadata": r[5],
                "created_at": r[6],
                "similarity": float(r[7])
            }
            for r in results
        ]
    
    def close(self):
        """Cierra la conexión."""
        if self._conn and not self._conn.closed:
            self._conn.close()
