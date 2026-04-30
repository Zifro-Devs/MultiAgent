"""Sistema de Memoria de Conocimiento Auto-Aprendizaje.

Guarda SOLO conocimiento útil extraído por la IA después de cada proyecto:
patrones exitosos, anti-patrones, preferencias de usuarios, decisiones técnicas, etc.
La IA decide qué vale la pena recordar. No se guardan chats.
"""

from __future__ import annotations

import json
import logging
from typing import List, Optional, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)

# Categorías de conocimiento que el sistema puede aprender
KNOWLEDGE_CATEGORIES = [
    "patron_exitoso",       # Algo que funcionó bien y vale repetir
    "anti_patron",          # Algo que causó problemas, evitar
    "preferencia_usuario",  # Lo que los usuarios piden frecuentemente
    "decision_tecnica",     # Stack, arquitectura, librerías que funcionaron
    "solucion_problema",    # Cómo se resolvió un problema específico
    "estructura_proyecto",  # Cómo se organizó el código exitosamente
    "integracion",          # APIs, servicios externos que se conectaron bien
    "error_comun",          # Errores frecuentes y cómo evitarlos
]


class KnowledgeMemory:
    """Gestiona la base de conocimiento vectorizada del sistema."""

    def __init__(self, db_url: str, embedding_model: str = "all-MiniLM-L6-v2"):
        self.db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        self.embedding_model_name = embedding_model
        self._encoder = None
        self._conn = None

    @property
    def encoder(self):
        if self._encoder is None:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
            logging.getLogger("transformers").setLevel(logging.ERROR)
            logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(self.embedding_model_name, local_files_only=False)
        return self._encoder

    def get_connection(self):
        if self._conn is None or self._conn.closed:
            import psycopg
            self._conn = psycopg.connect(self.db_url)
        return self._conn

    def ensure_table(self):
        """Crea la tabla knowledge_base si no existe."""
        conn = self.get_connection()
        cur = conn.cursor()
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id SERIAL PRIMARY KEY,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                insight TEXT NOT NULL,
                context TEXT,
                embedding vector(384),
                project_type TEXT,
                tags TEXT[],
                usefulness_score FLOAT DEFAULT 1.0,
                times_retrieved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_base_embedding_idx
            ON knowledge_base
            USING hnsw (embedding vector_cosine_ops);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_base_category_idx
            ON knowledge_base (category);
        """)
        conn.commit()
        cur.close()
        logger.info("Tabla knowledge_base lista")

    def store_insight(
        self,
        category: str,
        title: str,
        insight: str,
        context: Optional[str] = None,
        project_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Guarda un insight en la base de conocimiento.

        Args:
            category: Tipo de conocimiento (ver KNOWLEDGE_CATEGORIES)
            title: Título corto descriptivo
            insight: El conocimiento en sí, concreto y accionable
            context: Contexto adicional de dónde vino este conocimiento
            project_type: Tipo de proyecto (web, api, mobile, etc.)
            tags: Etiquetas para facilitar búsqueda

        Returns:
            True si se guardó correctamente
        """
        try:
            # El texto que se vectoriza combina título + insight para mejor semántica
            text_to_embed = f"{title}: {insight}"
            embedding = self.encoder.encode(text_to_embed, convert_to_numpy=True)

            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO knowledge_base
                    (category, title, insight, context, embedding, project_type, tags)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                category,
                title,
                insight,
                context,
                embedding.tolist(),
                project_type,
                tags or [],
            ))
            conn.commit()
            cur.close()
            logger.info(f"Conocimiento guardado: [{category}] {title}")
            return True
        except Exception as e:
            logger.error(f"Error guardando insight: {e}")
            return False

    def search_relevant_knowledge(
        self,
        query: str,
        limit: int = 8,
        category: Optional[str] = None,
        min_similarity: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """Busca conocimiento relevante para una consulta.

        Args:
            query: Descripción del proyecto o pregunta actual
            limit: Máximo de resultados
            category: Filtrar por categoría específica
            min_similarity: Similitud mínima (0-1)

        Returns:
            Lista de insights ordenados por relevancia
        """
        try:
            query_embedding = self.encoder.encode(query, convert_to_numpy=True)

            conn = self.get_connection()
            cur = conn.cursor()

            sql = """
                SELECT
                    id, category, title, insight, context,
                    project_type, tags, usefulness_score, times_retrieved,
                    1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_base
            """
            params: list = [query_embedding.tolist()]

            if category:
                sql += " WHERE category = %s"
                params.append(category)

            sql += """
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([query_embedding.tolist(), limit * 2])  # traer más, filtrar por similitud

            cur.execute(sql, params)
            rows = cur.fetchall()

            # Registrar que estos insights fueron recuperados (feedback loop)
            ids_retrieved = [r[0] for r in rows if float(r[9]) >= min_similarity]
            if ids_retrieved:
                cur.execute("""
                    UPDATE knowledge_base
                    SET times_retrieved = times_retrieved + 1,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ANY(%s)
                """, (ids_retrieved,))
                conn.commit()

            cur.close()

            results = [
                {
                    "id": r[0],
                    "category": r[1],
                    "title": r[2],
                    "insight": r[3],
                    "context": r[4],
                    "project_type": r[5],
                    "tags": r[6],
                    "usefulness_score": float(r[7]),
                    "times_retrieved": r[8],
                    "similarity": float(r[9]),
                }
                for r in rows
                if float(r[9]) >= min_similarity
            ]

            return results[:limit]

        except Exception as e:
            logger.error(f"Error buscando conocimiento: {e}")
            return []

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de la base de conocimiento."""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM knowledge_base;")
            total = cur.fetchone()[0]
            cur.execute("""
                SELECT category, COUNT(*) as count
                FROM knowledge_base
                GROUP BY category
                ORDER BY count DESC;
            """)
            by_category = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute("""
                SELECT title, times_retrieved
                FROM knowledge_base
                ORDER BY times_retrieved DESC
                LIMIT 5;
            """)
            most_used = [{"title": r[0], "times_retrieved": r[1]} for r in cur.fetchall()]
            cur.close()
            return {
                "total_insights": total,
                "by_category": by_category,
                "most_used": most_used,
            }
        except Exception as e:
            logger.error(f"Error obteniendo stats: {e}")
            return {"total_insights": 0, "by_category": {}, "most_used": []}

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()
