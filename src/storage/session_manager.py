"""Session Manager — Gestiona sesiones persistentes y memoria de largo plazo.

Permite continuar conversaciones anteriores y mantener contexto entre ejecuciones.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

logger = logging.getLogger(__name__)


class SessionManager:
    """Gestiona sesiones de usuario y memoria de largo plazo."""

    def __init__(self, db):
        """Inicializa el gestor de sesiones con una conexión a la base de datos.
        
        Args:
            db: Instancia de PostgresDb o SqliteDb de Agno
        """
        self.db = db
        self._ensure_tables()

    def _ensure_tables(self):
        """Asegura que las tablas necesarias existan."""
        try:
            # Las tablas ya son creadas por Agno, solo verificamos
            logger.debug("Verificando tablas de sesiones...")
        except Exception as e:
            logger.warning(f"Error verificando tablas: {e}")

    def create_session(self, user_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Crea una nueva sesión y retorna su ID.
        
        Args:
            user_id: ID opcional del usuario (para multi-usuario)
            metadata: Metadata adicional para la sesión
            
        Returns:
            session_id: UUID de la nueva sesión
        """
        session_id = str(uuid4())
        logger.info(f"Nueva sesión creada: {session_id} (usuario: {user_id or 'anónimo'})")
        
        # Agno crea la sesión automáticamente al primer run
        # Aquí solo generamos el ID
        return session_id

    def get_active_sessions(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene todas las sesiones activas.
        
        Args:
            user_id: Filtrar por usuario específico (opcional)
            limit: Número máximo de sesiones a retornar
            
        Returns:
            Lista de diccionarios con información de sesiones
        """
        try:
            # Query directo a la base de datos
            if hasattr(self.db, 'execute'):
                # PostgreSQL
                query = """
                    SELECT 
                        s.session_id,
                        s.user_id,
                        s.created_at,
                        s.updated_at,
                        COUNT(DISTINCT r.run_id) as run_count,
                        COUNT(m.id) as message_count,
                        MAX(m.created_at) as last_message_at
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                """
                
                if user_id:
                    query += " WHERE s.user_id = %s"
                    params = [user_id]
                else:
                    params = []
                
                query += """
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                    ORDER BY s.updated_at DESC
                    LIMIT %s
                """
                params.append(limit)
                
                result = self.db.execute(query, params)
                
                sessions = []
                for row in result:
                    sessions.append({
                        "session_id": row[0],
                        "user_id": row[1] or "anónimo",
                        "created_at": row[2],
                        "updated_at": row[3],
                        "run_count": row[4] or 0,
                        "message_count": row[5] or 0,
                        "last_message_at": row[6],
                    })
                
                logger.info(f"Sesiones encontradas: {len(sessions)}")
                return sessions
                
            else:
                # SQLite - usar conexión directa
                import sqlite3
                from pathlib import Path
                
                # Obtener ruta de la DB desde el objeto db
                db_file = getattr(self.db, 'db_file', 'data/devteam.db')
                
                if not Path(db_file).exists():
                    logger.warning(f"Base de datos no encontrada: {db_file}")
                    return []
                
                conn = sqlite3.connect(db_file)
                cur = conn.cursor()
                
                query = """
                    SELECT 
                        s.session_id,
                        s.user_id,
                        s.created_at,
                        s.updated_at,
                        COUNT(DISTINCT r.run_id) as run_count,
                        COUNT(m.id) as message_count,
                        MAX(m.created_at) as last_message_at
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                """
                
                if user_id:
                    query += " WHERE s.user_id = ?"
                    params = [user_id]
                else:
                    params = []
                
                query += """
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                    ORDER BY s.updated_at DESC
                    LIMIT ?
                """
                params.append(limit)
                
                cur.execute(query, params)
                rows = cur.fetchall()
                
                sessions = []
                for row in rows:
                    sessions.append({
                        "session_id": row[0],
                        "user_id": row[1] or "anónimo",
                        "created_at": row[2],
                        "updated_at": row[3],
                        "run_count": row[4] or 0,
                        "message_count": row[5] or 0,
                        "last_message_at": row[6],
                    })
                
                cur.close()
                conn.close()
                
                logger.info(f"Sesiones encontradas: {len(sessions)}")
                return sessions
                
        except Exception as e:
            logger.error(f"Error obteniendo sesiones: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_session_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene un resumen detallado de una sesión específica.
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Diccionario con resumen de la sesión o None si no existe
        """
        try:
            if hasattr(self.db, 'execute'):
                # PostgreSQL
                query = """
                    SELECT 
                        s.session_id,
                        s.user_id,
                        s.created_at,
                        s.updated_at,
                        COUNT(DISTINCT r.run_id) as run_count,
                        COUNT(m.id) as message_count,
                        MAX(m.created_at) as last_message_at,
                        MIN(m.created_at) as first_message_at
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                    WHERE s.session_id = %s
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                """
                
                result = self.db.execute(query, [session_id])
                row = result[0] if result else None
                
            else:
                # SQLite
                import sqlite3
                from pathlib import Path
                
                db_file = getattr(self.db, 'db_file', 'data/devteam.db')
                
                if not Path(db_file).exists():
                    return None
                
                conn = sqlite3.connect(db_file)
                cur = conn.cursor()
                
                query = """
                    SELECT 
                        s.session_id,
                        s.user_id,
                        s.created_at,
                        s.updated_at,
                        COUNT(DISTINCT r.run_id) as run_count,
                        COUNT(m.id) as message_count,
                        MAX(m.created_at) as last_message_at,
                        MIN(m.created_at) as first_message_at
                    FROM sessions s
                    LEFT JOIN runs r ON s.session_id = r.session_id
                    LEFT JOIN messages m ON r.run_id = m.run_id
                    WHERE s.session_id = ?
                    GROUP BY s.session_id, s.user_id, s.created_at, s.updated_at
                """
                
                cur.execute(query, [session_id])
                row = cur.fetchone()
                cur.close()
                conn.close()
            
            if not row:
                logger.warning(f"Sesión no encontrada: {session_id}")
                return None
            
            summary = {
                "session_id": row[0],
                "user_id": row[1] or "anónimo",
                "created_at": row[2],
                "updated_at": row[3],
                "run_count": row[4] or 0,
                "message_count": row[5] or 0,
                "last_message_at": row[6],
                "first_message_at": row[7],
            }
            
            logger.info(f"Resumen de sesión obtenido: {session_id}")
            return summary
            
        except Exception as e:
            logger.error(f"Error obteniendo resumen de sesión: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_session_messages(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Obtiene los mensajes de una sesión.
        
        Args:
            session_id: ID de la sesión
            limit: Número máximo de mensajes
            
        Returns:
            Lista de mensajes ordenados cronológicamente
        """
        try:
            if hasattr(self.db, 'execute'):
                # PostgreSQL
                query = """
                    SELECT m.role, m.content, m.created_at
                    FROM messages m
                    JOIN runs r ON m.run_id = r.run_id
                    WHERE r.session_id = %s
                    ORDER BY m.created_at ASC
                    LIMIT %s
                """
                result = self.db.execute(query, [session_id, limit])
                
            else:
                # SQLite
                import sqlite3
                from pathlib import Path
                
                db_file = getattr(self.db, 'db_file', 'data/devteam.db')
                
                if not Path(db_file).exists():
                    return []
                
                conn = sqlite3.connect(db_file)
                cur = conn.cursor()
                
                query = """
                    SELECT m.role, m.content, m.created_at
                    FROM messages m
                    JOIN runs r ON m.run_id = r.run_id
                    WHERE r.session_id = ?
                    ORDER BY m.created_at ASC
                    LIMIT ?
                """
                
                cur.execute(query, [session_id, limit])
                result = cur.fetchall()
                cur.close()
                conn.close()
            
            messages = []
            for row in result:
                messages.append({
                    "role": row[0],
                    "content": row[1],
                    "created_at": row[2],
                })
            
            logger.info(f"Mensajes obtenidos: {len(messages)} para sesión {session_id}")
            return messages
            
        except Exception as e:
            logger.error(f"Error obteniendo mensajes: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """Elimina una sesión y su historial completo.
        
        Args:
            session_id: ID de la sesión a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            if hasattr(self.db, 'execute'):
                # PostgreSQL - eliminar en cascada
                queries = [
                    "DELETE FROM messages WHERE run_id IN (SELECT run_id FROM runs WHERE session_id = %s)",
                    "DELETE FROM agent_sessions WHERE session_id = %s",
                    "DELETE FROM runs WHERE session_id = %s",
                    "DELETE FROM sessions WHERE session_id = %s",
                ]
                
                for query in queries:
                    self.db.execute(query, [session_id])
                
            else:
                # SQLite
                import sqlite3
                from pathlib import Path
                
                db_file = getattr(self.db, 'db_file', 'data/devteam.db')
                
                if not Path(db_file).exists():
                    return False
                
                conn = sqlite3.connect(db_file)
                cur = conn.cursor()
                
                queries = [
                    "DELETE FROM messages WHERE run_id IN (SELECT run_id FROM runs WHERE session_id = ?)",
                    "DELETE FROM agent_sessions WHERE session_id = ?",
                    "DELETE FROM runs WHERE session_id = ?",
                    "DELETE FROM sessions WHERE session_id = ?",
                ]
                
                for query in queries:
                    cur.execute(query, [session_id])
                
                conn.commit()
                cur.close()
                conn.close()
            
            logger.info(f"Sesión eliminada: {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando sesión: {e}")
            import traceback
            traceback.print_exc()
            return False
