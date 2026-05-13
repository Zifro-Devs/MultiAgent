"""Memoria de conocimiento con aprendizaje continuo.

Este módulo implementa una base de conocimiento vectorizada que:

1. Deduplica insights por similitud semántica: si un insight muy parecido
   ya existe, refuerza el existente en lugar de crear otro.
2. Aplica refuerzo positivo y negativo: cada insight tiene un `usefulness_score`
   que sube cuando se recupera en proyectos exitosos y baja cuando se recupera
   en proyectos con gates fallidos.
3. Aplica decay temporal: insights no usados pierden relevancia gradualmente.
4. Hace hybrid search: combina similitud vectorial + score de utilidad +
   recencia para priorizar conocimiento realmente útil.
5. Consolida: encuentra clusters de insights muy similares y permite fusionarlos.
6. Olvida selectivamente: insights con score muy bajo pueden archivarse.

La tabla `knowledge_base` es compatible con el esquema anterior y se amplía
con columnas nuevas de forma no-destructiva (ADD COLUMN IF NOT EXISTS).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Categorías de conocimiento ──────────────────────────────────────

KNOWLEDGE_CATEGORIES = [
    "patron_exitoso",        # Algo que funcionó bien y vale repetir
    "anti_patron",           # Algo que causó problemas — evitar
    "preferencia_usuario",   # Lo que los usuarios piden frecuentemente
    "decision_tecnica",      # Stack, arquitectura, librerías que funcionaron
    "solucion_problema",     # Cómo se resolvió un problema específico
    "estructura_proyecto",   # Cómo se organizó el código de forma exitosa
    "integracion",           # APIs, servicios externos que se conectaron bien
    "error_comun",           # Errores frecuentes y cómo evitarlos
    # Nuevas categorías derivadas de las señales de aprendizaje:
    "error_compilador",      # Errores detectados por el code validator
    "hallazgo_validacion",   # Hallazgos reales del agente de validación
    "falla_quality_gate",    # Patrones que fallan quality gates
    "convencion_nombres",    # Patrones de naming que el usuario prefiere
]

# ── Parámetros de aprendizaje ───────────────────────────────────────

# Similitud por encima de la cual se considera duplicado (reforzar, no crear)
DEDUP_SIMILARITY_THRESHOLD = 0.88

# Score inicial cuando se crea un insight nuevo
DEFAULT_USEFULNESS_SCORE = 1.0

# Delta de refuerzo cuando un insight se usó en proyecto exitoso
POSITIVE_REINFORCEMENT = 0.25

# Delta negativo cuando un insight se usó en proyecto con gates fallidos
NEGATIVE_REINFORCEMENT = 0.15

# Umbral mínimo para seguir apareciendo en búsquedas (bajo esto, "archivado")
ARCHIVE_SCORE_THRESHOLD = 0.1

# Decay por día sin uso (multiplicativo)
DAILY_DECAY_FACTOR = 0.995


@dataclass
class InsightRecord:
    """Representación de un insight recuperado de la BD."""

    id: int
    category: str
    title: str
    insight: str
    context: Optional[str]
    project_type: Optional[str]
    tags: List[str]
    usefulness_score: float
    times_retrieved: int
    reinforcement_count: int
    similarity: float = 0.0
    created_at: Optional[datetime] = None
    last_retrieved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "insight": self.insight,
            "context": self.context,
            "project_type": self.project_type,
            "tags": self.tags,
            "usefulness_score": self.usefulness_score,
            "times_retrieved": self.times_retrieved,
            "reinforcement_count": self.reinforcement_count,
            "similarity": self.similarity,
        }


class KnowledgeMemory:
    """Base de conocimiento vectorizada con aprendizaje continuo."""

    def __init__(
        self,
        db_url: str,
        embedding_model: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.db_url = db_url.replace("postgresql+psycopg://", "postgresql://")
        self.embedding_model_name = embedding_model
        self._encoder = None
        self._conn = None

    # ── Conexión y encoder lazy ────────────────────────────────────

    @property
    def encoder(self):
        if self._encoder is None:
            import warnings
            warnings.filterwarnings("ignore", category=UserWarning)
            logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
            logging.getLogger("transformers").setLevel(logging.ERROR)
            logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
            from sentence_transformers import SentenceTransformer
            self._encoder = SentenceTransformer(
                self.embedding_model_name, local_files_only=False
            )
        return self._encoder

    def get_connection(self):
        if self._conn is None or self._conn.closed:
            import psycopg
            self._conn = psycopg.connect(self.db_url)
        return self._conn

    def _encode(self, text: str) -> np.ndarray:
        return self.encoder.encode(text, convert_to_numpy=True)

    # ── Schema management ──────────────────────────────────────────

    def ensure_table(self) -> None:
        """Crea o migra la tabla knowledge_base de forma idempotente."""
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
        # Columnas adicionales para el sistema de refuerzo (ADD IF NOT EXISTS)
        extra_cols = [
            ("reinforcement_count", "INTEGER DEFAULT 1"),
            ("last_retrieved_at", "TIMESTAMP"),
            ("positive_feedback", "INTEGER DEFAULT 0"),
            ("negative_feedback", "INTEGER DEFAULT 0"),
            ("archived", "BOOLEAN DEFAULT FALSE"),
            ("source_signal", "TEXT"),  # p.ej. 'project_completion', 'compiler_error'
        ]
        for col, ddl in extra_cols:
            cur.execute(
                f"ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS {col} {ddl};"
            )
        # Índices
        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_base_embedding_idx
            ON knowledge_base USING hnsw (embedding vector_cosine_ops);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_base_category_idx
            ON knowledge_base (category);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS knowledge_base_score_idx
            ON knowledge_base (usefulness_score DESC) WHERE archived = FALSE;
        """)
        conn.commit()
        cur.close()
        logger.info("Tabla knowledge_base lista (con extensiones de aprendizaje)")

    # ── Escritura con deduplicación ────────────────────────────────

    def store_insight(
        self,
        category: str,
        title: str,
        insight: str,
        context: Optional[str] = None,
        project_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source_signal: str = "project_completion",
    ) -> bool:
        """Guarda un insight deduplicándolo semánticamente.

        Si existe un insight con similitud >= DEDUP_SIMILARITY_THRESHOLD y
        la misma categoría, refuerza el existente en lugar de crear otro.

        Returns:
            True si se creó uno nuevo o se reforzó uno existente.
        """
        try:
            text_to_embed = f"{title}: {insight}"
            embedding = self._encode(text_to_embed)

            # Buscar si ya existe uno muy similar en la misma categoría
            existing = self._find_near_duplicate(embedding, category)
            if existing is not None:
                self._reinforce_existing(existing["id"], extra_tags=tags or [])
                logger.info(
                    "Insight deduplicado: refuerzo sobre id=%s (sim=%.2f) — %s",
                    existing["id"], existing["similarity"], title[:60],
                )
                return True

            # Insertar nuevo
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO knowledge_base
                    (category, title, insight, context, embedding,
                     project_type, tags, usefulness_score, reinforcement_count,
                     source_signal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """, (
                category,
                title,
                insight,
                context,
                embedding.tolist(),
                project_type,
                tags or [],
                DEFAULT_USEFULNESS_SCORE,
                source_signal,
            ))
            conn.commit()
            cur.close()
            logger.info("Insight guardado: [%s] %s", category, title[:60])
            return True
        except Exception as e:
            logger.error("Error guardando insight: %s", e)
            return False

    def _find_near_duplicate(
        self, embedding: np.ndarray, category: str
    ) -> Optional[Dict[str, Any]]:
        """Busca un insight muy similar (misma categoría) para deduplicar."""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT id, 1 - (embedding <=> %s::vector) AS similarity
                FROM knowledge_base
                WHERE category = %s AND archived = FALSE
                ORDER BY embedding <=> %s::vector
                LIMIT 1
            """, (embedding.tolist(), category, embedding.tolist()))
            row = cur.fetchone()
            cur.close()
            if row and float(row[1]) >= DEDUP_SIMILARITY_THRESHOLD:
                return {"id": row[0], "similarity": float(row[1])}
            return None
        except Exception as e:
            logger.warning("Error en dedup lookup: %s", e)
            return None

    def _reinforce_existing(self, insight_id: int, extra_tags: List[str]) -> None:
        """Refuerza un insight existente al reaparecer en otro proyecto."""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("""
                UPDATE knowledge_base
                SET reinforcement_count = reinforcement_count + 1,
                    usefulness_score = LEAST(5.0, usefulness_score + %s),
                    tags = ARRAY(SELECT DISTINCT unnest(COALESCE(tags, '{}') || %s::TEXT[])),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (POSITIVE_REINFORCEMENT / 2, extra_tags, insight_id))
            conn.commit()
            cur.close()
        except Exception as e:
            logger.warning("Error reforzando insight %s: %s", insight_id, e)

    # ── Búsqueda con hybrid scoring ────────────────────────────────

    def search_relevant_knowledge(
        self,
        query: str,
        limit: int = 8,
        category: Optional[str] = None,
        min_similarity: float = 0.4,
        project_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Búsqueda híbrida: similitud + score de utilidad + recencia.

        El score final combina:
          similarity (0-1)
        + usefulness_score / 5 (0-1) — normalizado
        + recency_bonus (0-0.2) — últimos 30 días
        """
        try:
            query_embedding = self._encode(query)
            conn = self.get_connection()
            cur = conn.cursor()

            sql = """
                SELECT
                    id, category, title, insight, context,
                    project_type, tags, usefulness_score, times_retrieved,
                    COALESCE(reinforcement_count, 1) as reinforcement_count,
                    created_at, last_retrieved_at,
                    1 - (embedding <=> %s::vector) AS similarity,
                    EXTRACT(EPOCH FROM (NOW() - COALESCE(last_retrieved_at, created_at))) / 86400.0 AS days_since_use
                FROM knowledge_base
                WHERE archived = FALSE
            """
            params: List[Any] = [query_embedding.tolist()]

            if category:
                sql += " AND category = %s"
                params.append(category)
            if project_type:
                sql += " AND (project_type = %s OR project_type IS NULL)"
                params.append(project_type)

            # Traemos más candidatos para re-rankear con score híbrido
            sql += """
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """
            params.extend([query_embedding.tolist(), max(limit * 3, 15)])

            cur.execute(sql, params)
            rows = cur.fetchall()
            cur.close()

            # Re-ranking híbrido
            candidates: List[Dict[str, Any]] = []
            for r in rows:
                similarity = float(r[12])
                if similarity < min_similarity:
                    continue
                usefulness = float(r[7])
                days = float(r[13]) if r[13] is not None else 9999.0
                recency_bonus = max(0.0, 0.2 * (1 - min(days / 30.0, 1.0)))
                hybrid_score = (
                    similarity * 0.60
                    + (usefulness / 5.0) * 0.25
                    + recency_bonus * 0.15
                )
                candidates.append({
                    "id": r[0],
                    "category": r[1],
                    "title": r[2],
                    "insight": r[3],
                    "context": r[4],
                    "project_type": r[5],
                    "tags": r[6] or [],
                    "usefulness_score": usefulness,
                    "times_retrieved": r[8],
                    "reinforcement_count": r[9],
                    "similarity": similarity,
                    "hybrid_score": hybrid_score,
                })

            # Ordenar por score híbrido descendente
            candidates.sort(key=lambda c: c["hybrid_score"], reverse=True)
            results = candidates[:limit]

            # Registrar recuperación (feedback loop input)
            if results:
                ids_retrieved = [c["id"] for c in results]
                cur = self.get_connection().cursor()
                cur.execute("""
                    UPDATE knowledge_base
                    SET times_retrieved = times_retrieved + 1,
                        last_retrieved_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ANY(%s)
                """, (ids_retrieved,))
                self.get_connection().commit()
                cur.close()

            return results
        except Exception as e:
            logger.error("Error buscando conocimiento: %s", e)
            return []

    # ── Feedback loop (refuerzo / castigo) ─────────────────────────

    def apply_feedback(self, insight_ids: List[int], positive: bool) -> None:
        """Aplica feedback a insights usados en un proyecto.

        Si el proyecto terminó bien (pocos gates fallidos, pocos errores de
        compilación), positive=True y los insights usados suben de score.
        Si terminó con problemas, positive=False y bajan.
        """
        if not insight_ids:
            return
        try:
            delta = POSITIVE_REINFORCEMENT if positive else -NEGATIVE_REINFORCEMENT
            col = "positive_feedback" if positive else "negative_feedback"
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute(f"""
                UPDATE knowledge_base
                SET usefulness_score = GREATEST(0.0, LEAST(5.0, usefulness_score + %s)),
                    {col} = {col} + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
            """, (delta, insight_ids))
            # Archivar los que quedan con score muy bajo tras feedback negativo
            cur.execute("""
                UPDATE knowledge_base
                SET archived = TRUE
                WHERE id = ANY(%s) AND usefulness_score < %s
            """, (insight_ids, ARCHIVE_SCORE_THRESHOLD))
            conn.commit()
            cur.close()
            logger.info(
                "Feedback %s aplicado a %d insights (delta=%.2f)",
                "positivo" if positive else "negativo", len(insight_ids), delta,
            )
        except Exception as e:
            logger.error("Error aplicando feedback: %s", e)

    # ── Decay temporal ─────────────────────────────────────────────

    def apply_temporal_decay(self, days_threshold: int = 7) -> int:
        """Reduce el score de insights no usados por N días.

        Se ejecuta periódicamente (p.ej. al inicio de una sesión). Simula
        el "olvido" de conocimiento que no se revalida con uso real.

        Returns:
            Número de insights afectados.
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            # Aplicar decay multiplicativo por día sin uso
            cur.execute("""
                UPDATE knowledge_base
                SET usefulness_score = GREATEST(0.0, usefulness_score * POWER(%s,
                    GREATEST(0, EXTRACT(EPOCH FROM (NOW() - COALESCE(last_retrieved_at, created_at))) / 86400.0 - %s)
                )),
                    updated_at = CURRENT_TIMESTAMP
                WHERE archived = FALSE
                  AND (last_retrieved_at IS NULL OR last_retrieved_at < NOW() - INTERVAL '%s days')
            """, (DAILY_DECAY_FACTOR, days_threshold, days_threshold))
            affected = cur.rowcount
            # Archivar los que cayeron bajo el umbral
            cur.execute("""
                UPDATE knowledge_base
                SET archived = TRUE
                WHERE archived = FALSE AND usefulness_score < %s
            """, (ARCHIVE_SCORE_THRESHOLD,))
            archived = cur.rowcount
            conn.commit()
            cur.close()
            logger.info(
                "Decay aplicado: %d insights, %d archivados por score bajo",
                affected, archived,
            )
            return affected
        except Exception as e:
            logger.error("Error aplicando decay: %s", e)
            return 0

    # ── Consolidación (merge de clusters similares) ────────────────

    @staticmethod
    def _parse_embedding(raw) -> np.ndarray:
        """Convierte el embedding de pgvector a np.ndarray.

        pgvector devuelve el valor como lista si el adaptador está
        registrado, o como string "[v1,v2,...]" si no lo está. Soportamos
        ambos casos para no depender de configuración externa.
        """
        if isinstance(raw, (list, tuple)):
            return np.asarray(raw, dtype=np.float32)
        if isinstance(raw, np.ndarray):
            return raw.astype(np.float32, copy=False)
        if isinstance(raw, str):
            # Formato "[v1,v2,...]" o "(v1,v2,...)"
            cleaned = raw.strip().lstrip("[(").rstrip("])")
            if not cleaned:
                return np.zeros(0, dtype=np.float32)
            parts = cleaned.split(",")
            return np.fromiter((float(p) for p in parts), dtype=np.float32, count=len(parts))
        # Fallback: intentar convertir lo que sea
        return np.asarray(raw, dtype=np.float32)

    def consolidate_clusters(
        self,
        cluster_threshold: float = 0.90,
        max_clusters: int = 50,
    ) -> int:
        """Encuentra clusters de insights muy similares y los fusiona.

        Fusión:
          - Mantiene el insight con mayor reinforcement_count como canónico.
          - Archiva los duplicados.
          - Transfiere el reinforcement_count y positive_feedback de los
            archivados al canónico.

        Returns:
            Número de insights archivados por consolidación.
        """
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            # Traer insights activos agrupados por categoría
            cur.execute("""
                SELECT id, category, title, insight, embedding,
                       reinforcement_count, usefulness_score, positive_feedback
                FROM knowledge_base
                WHERE archived = FALSE
                ORDER BY category, reinforcement_count DESC
            """)
            rows = cur.fetchall()
            # Agrupar por categoría
            by_category: Dict[str, List[tuple]] = {}
            for r in rows:
                by_category.setdefault(r[1], []).append(r)

            archived_total = 0
            for category, items in by_category.items():
                if len(items) < 2:
                    continue
                # Para cada item, calcular similitud con los que vienen
                # después (los tenemos ordenados por reinforcement desc)
                archived_ids: set[int] = set()
                for i, a in enumerate(items):
                    if a[0] in archived_ids:
                        continue
                    if archived_total >= max_clusters:
                        break
                    a_emb = self._parse_embedding(a[4])
                    if a_emb.size == 0:
                        continue
                    a_norm = a_emb / (np.linalg.norm(a_emb) + 1e-9)
                    to_merge: List[int] = []
                    merge_reinforcement = 0
                    merge_positive = 0
                    for b in items[i + 1:]:
                        if b[0] in archived_ids:
                            continue
                        b_emb = self._parse_embedding(b[4])
                        if b_emb.size == 0 or b_emb.shape != a_emb.shape:
                            continue
                        b_norm = b_emb / (np.linalg.norm(b_emb) + 1e-9)
                        sim = float(np.dot(a_norm, b_norm))
                        if sim >= cluster_threshold:
                            to_merge.append(b[0])
                            merge_reinforcement += (b[5] or 0)
                            merge_positive += (b[7] or 0)

                    if to_merge:
                        # Archivar los duplicados
                        cur.execute("""
                            UPDATE knowledge_base
                            SET archived = TRUE,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ANY(%s)
                        """, (to_merge,))
                        # Reforzar el canónico con los counts sumados
                        cur.execute("""
                            UPDATE knowledge_base
                            SET reinforcement_count = reinforcement_count + %s,
                                positive_feedback = positive_feedback + %s,
                                usefulness_score = LEAST(5.0, usefulness_score + %s),
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (
                            merge_reinforcement,
                            merge_positive,
                            POSITIVE_REINFORCEMENT * len(to_merge) * 0.5,
                            a[0],
                        ))
                        archived_ids.update(to_merge)
                        archived_total += len(to_merge)

            conn.commit()
            cur.close()
            logger.info("Consolidación: %d insights archivados", archived_total)
            return archived_total
        except Exception as e:
            logger.error("Error en consolidación: %s", e)
            return 0

    # ── Estadísticas / observabilidad ─────────────────────────────

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Estadísticas del estado actual de la base de conocimiento."""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM knowledge_base WHERE archived = FALSE;")
            active = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM knowledge_base WHERE archived = TRUE;")
            archived = cur.fetchone()[0]
            cur.execute("""
                SELECT category, COUNT(*) as count, AVG(usefulness_score) as avg_score
                FROM knowledge_base
                WHERE archived = FALSE
                GROUP BY category
                ORDER BY count DESC;
            """)
            by_category = [
                {"category": r[0], "count": r[1], "avg_score": round(float(r[2] or 0), 2)}
                for r in cur.fetchall()
            ]
            cur.execute("""
                SELECT title, usefulness_score, reinforcement_count, times_retrieved
                FROM knowledge_base
                WHERE archived = FALSE
                ORDER BY usefulness_score DESC, reinforcement_count DESC
                LIMIT 10;
            """)
            top_insights = [
                {
                    "title": r[0],
                    "score": round(float(r[1]), 2),
                    "reinforcement": r[2],
                    "retrieved": r[3],
                }
                for r in cur.fetchall()
            ]
            cur.execute("""
                SELECT source_signal, COUNT(*)
                FROM knowledge_base
                WHERE archived = FALSE AND source_signal IS NOT NULL
                GROUP BY source_signal;
            """)
            by_signal = {r[0]: r[1] for r in cur.fetchall()}
            cur.close()
            return {
                "total_active": active,
                "total_archived": archived,
                "by_category": by_category,
                "by_signal": by_signal,
                "top_insights": top_insights,
            }
        except Exception as e:
            logger.error("Error obteniendo stats: %s", e)
            return {"total_active": 0, "total_archived": 0, "by_category": [], "top_insights": []}

    def close(self) -> None:
        if self._conn and not self._conn.closed:
            self._conn.close()
