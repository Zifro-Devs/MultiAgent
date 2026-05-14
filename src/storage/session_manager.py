"""Session Manager — Gestiona sesiones persistentes y memoria de largo plazo.

Detecta automáticamente si la BD es Supabase (PostgreSQL) o SQLite y usa el
driver apropiado, sin depender de la API interna del objeto db de Agno.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


def _is_postgres(db) -> bool:
    """Detecta si la BD es PostgreSQL/Supabase de forma robusta."""
    # Agno PostgresDb expone db_url
    if getattr(db, "db_url", None):
        return True
    # Algunos forks exponen connection_string
    if getattr(db, "connection_string", None):
        return True
    # Si la clase contiene 'Postgres' es claro
    return "Postgres" in type(db).__name__


def _get_pg_url(db) -> Optional[str]:
    """Extrae la URL de conexión PostgreSQL del objeto db."""
    url = getattr(db, "db_url", None) or getattr(db, "connection_string", None)
    if url:
        return url.replace("postgresql+psycopg://", "postgresql://")
    return None


class SessionManager:
    """Gestiona sesiones de usuario y memoria de largo plazo."""

    def __init__(self, db):
        self.db = db
        self.is_postgres = _is_postgres(db)
        self._ensure_tables()

    # ── Setup de tablas ────────────────────────────────────────────

    def _ensure_tables(self) -> None:
        """Crea las tablas necesarias si no existen (idempotente)."""
        try:
            if self.is_postgres:
                self._ensure_tables_postgres()
            else:
                self._ensure_tables_sqlite()
        except Exception as e:
            logger.warning(f"No se pudo verificar/crear tablas: {e}")

    def _ensure_tables_postgres(self) -> None:
        """Crea tablas en PostgreSQL/Supabase usando psycopg directo."""
        url = _get_pg_url(self.db)
        if not url:
            return
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id SERIAL PRIMARY KEY,
                        session_id TEXT UNIQUE NOT NULL,
                        user_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        id SERIAL PRIMARY KEY,
                        run_id TEXT UNIQUE NOT NULL,
                        session_id TEXT REFERENCES sessions(session_id),
                        agent_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id SERIAL PRIMARY KEY,
                        run_id TEXT REFERENCES runs(run_id),
                        role TEXT NOT NULL,
                        content TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS agent_sessions (
                        id SERIAL PRIMARY KEY,
                        agent_id TEXT NOT NULL,
                        session_id TEXT REFERENCES sessions(session_id),
                        data JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                conn.commit()
        logger.info("Tablas de sesiones verificadas en Supabase")

    def _ensure_tables_sqlite(self) -> None:
        """Crea tablas en SQLite local."""
        import sqlite3
        from pathlib import Path
        db_file = getattr(self.db, "db_file", "data/devteam.db")
        Path(db_file).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_file)
        try:
            cur = conn.cursor()
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT REFERENCES sessions(session_id),
                    agent_name TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT REFERENCES runs(run_id),
                    role TEXT,
                    content TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    session_id TEXT,
                    agent_id TEXT,
                    data TEXT,
                    created_at TEXT DEFAULT (datetime('now')),
                    PRIMARY KEY (session_id, agent_id)
                );
            """)
            conn.commit()
        finally:
            conn.close()
        logger.info("Tablas de sesiones verificadas en SQLite")

    # ── API pública ────────────────────────────────────────────────

    def create_session(
        self,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Crea una nueva sesión y retorna su ID."""
        session_id = str(uuid4())
        logger.info(f"Nueva sesión creada: {session_id} (usuario: {user_id or 'anónimo'})")
        return session_id

    def get_active_sessions(
        self, user_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lista sesiones activas con stats agregados."""
        try:
            if self.is_postgres:
                rows = self._query_postgres(
                    """
                    SELECT s.session_id, s.user_id, s.created_at, s.updated_at,
                           COUNT(DISTINCT r.run_id), COUNT(m.id), MAX(m.created_at)
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                    {where}
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                    ORDER BY s.updated_at DESC
                    LIMIT %s
                    """,
                    user_id,
                    limit,
                    placeholder="%s",
                )
            else:
                rows = self._query_sqlite(
                    """
                    SELECT s.session_id, s.user_id, s.created_at, s.updated_at,
                           COUNT(DISTINCT r.run_id), COUNT(m.id), MAX(m.created_at)
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                    {where}
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                    ORDER BY s.updated_at DESC
                    LIMIT ?
                    """,
                    user_id,
                    limit,
                    placeholder="?",
                )

            sessions = [
                {
                    "session_id": r[0],
                    "user_id": r[1] or "anónimo",
                    "created_at": r[2],
                    "updated_at": r[3],
                    "run_count": r[4] or 0,
                    "message_count": r[5] or 0,
                    "last_message_at": r[6],
                }
                for r in rows
            ]
            logger.info(f"Sesiones encontradas: {len(sessions)}")
            return sessions
        except Exception as e:
            logger.error(f"Error obteniendo sesiones: {e}")
            return []

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Resumen de una sesión específica."""
        try:
            if self.is_postgres:
                rows = self._exec_postgres(
                    """
                    SELECT s.session_id, s.user_id, s.created_at, s.updated_at,
                           COUNT(DISTINCT r.run_id), COUNT(m.id),
                           MAX(m.created_at), MIN(m.created_at)
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                    WHERE s.session_id = %s
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                    """,
                    [session_id],
                )
            else:
                rows = self._exec_sqlite(
                    """
                    SELECT s.session_id, s.user_id, s.created_at, s.updated_at,
                           COUNT(DISTINCT r.run_id), COUNT(m.id),
                           MAX(m.created_at), MIN(m.created_at)
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                    WHERE s.session_id = ?
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                    """,
                    [session_id],
                )

            if not rows:
                return None
            r = rows[0]
            return {
                "session_id": r[0],
                "user_id": r[1] or "anónimo",
                "created_at": r[2],
                "updated_at": r[3],
                "run_count": r[4] or 0,
                "message_count": r[5] or 0,
                "last_message_at": r[6],
                "first_message_at": r[7],
            }
        except Exception as e:
            logger.error(f"Error obteniendo resumen: {e}")
            return None

    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Mensajes de una sesión ordenados cronológicamente."""
        try:
            if self.is_postgres:
                rows = self._exec_postgres(
                    """
                    SELECT m.role, m.content, m.created_at
                    FROM messages m
                    JOIN runs r ON m.run_id = r.run_id
                    WHERE r.session_id = %s
                    ORDER BY m.created_at ASC
                    LIMIT %s
                    """,
                    [session_id, limit],
                )
            else:
                rows = self._exec_sqlite(
                    """
                    SELECT m.role, m.content, m.created_at
                    FROM messages m
                    JOIN runs r ON m.run_id = r.run_id
                    WHERE r.session_id = ?
                    ORDER BY m.created_at ASC
                    LIMIT ?
                    """,
                    [session_id, limit],
                )
            return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in rows]
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Elimina una sesión y su historial completo."""
        try:
            queries_pg = [
                "DELETE FROM messages WHERE run_id IN (SELECT run_id FROM runs WHERE session_id = %s)",
                "DELETE FROM agent_sessions WHERE session_id = %s",
                "DELETE FROM runs WHERE session_id = %s",
                "DELETE FROM sessions WHERE session_id = %s",
            ]
            queries_sq = [q.replace("%s", "?") for q in queries_pg]
            if self.is_postgres:
                for q in queries_pg:
                    self._exec_postgres(q, [session_id], fetch=False)
            else:
                for q in queries_sq:
                    self._exec_sqlite(q, [session_id], fetch=False)
            logger.info(f"Sesión eliminada: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando sesión: {e}")
            return False

    # ── Helpers internos ───────────────────────────────────────────

    def _query_postgres(self, sql: str, user_id: Optional[str], limit: int, placeholder: str) -> List[tuple]:
        where = ""
        params: List[Any] = []
        if user_id:
            where = f"WHERE s.user_id = {placeholder}"
            params.append(user_id)
        params.append(limit)
        return self._exec_postgres(sql.format(where=where), params)

    def _query_sqlite(self, sql: str, user_id: Optional[str], limit: int, placeholder: str) -> List[tuple]:
        where = ""
        params: List[Any] = []
        if user_id:
            where = f"WHERE s.user_id = {placeholder}"
            params.append(user_id)
        params.append(limit)
        return self._exec_sqlite(sql.format(where=where), params)

    def _exec_postgres(self, sql: str, params: List[Any], fetch: bool = True) -> List[tuple]:
        url = _get_pg_url(self.db)
        if not url:
            return []
        import psycopg
        with psycopg.connect(url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                if fetch:
                    return cur.fetchall()
                conn.commit()
                return []

    def _exec_sqlite(self, sql: str, params: List[Any], fetch: bool = True) -> List[tuple]:
        import sqlite3
        from pathlib import Path
        db_file = getattr(self.db, "db_file", "data/devteam.db")
        if not Path(db_file).exists():
            return []
        conn = sqlite3.connect(db_file)
        try:
            cur = conn.cursor()
            cur.execute(sql, params)
            if fetch:
                rows = cur.fetchall()
                cur.close()
                return rows
            conn.commit()
            return []
        finally:
            conn.close()
