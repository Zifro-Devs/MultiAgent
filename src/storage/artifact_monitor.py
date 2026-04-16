"""Monitor de Artefactos.

Observa la carpeta de artefactos y almacena automáticamente
los archivos generados en la memoria vectorizada.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src.storage.memory_integration import MemoryIntegration

logger = logging.getLogger(__name__)


class ArtifactMonitor:
    """Monitorea y almacena artefactos generados."""

    def __init__(self, artifacts_path: Path, memory: MemoryIntegration):
        """Inicializa el monitor de artefactos.
        
        Args:
            artifacts_path: Ruta a la carpeta de artefactos
            memory: Instancia de MemoryIntegration
        """
        self.artifacts_path = artifacts_path
        self.memory = memory
        self._processed_files = set()

    def scan_and_store(self, session_id: str):
        """Escanea la carpeta de artefactos y almacena archivos nuevos.
        
        Args:
            session_id: ID de la sesión actual
        """
        if not self.memory.is_enabled():
            return
        
        try:
            # Obtener todos los archivos de código
            code_extensions = {'.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c', '.cs', '.jsx', '.tsx'}
            
            for file_path in self.artifacts_path.rglob("*"):
                if not file_path.is_file():
                    continue
                
                # Saltar archivos ya procesados
                if str(file_path) in self._processed_files:
                    continue
                
                # Saltar archivos no-código
                file_ext = file_path.suffix.lower()
                if file_ext not in code_extensions:
                    continue
                
                # Leer y almacenar
                try:
                    content = file_path.read_text(encoding='utf-8')
                    relative_path = str(file_path.relative_to(self.artifacts_path)).replace("\\", "/")
                    
                    # Determinar tipo de código
                    code_type = "module"
                    if "class " in content:
                        code_type = "class"
                    elif "def " in content or "function " in content:
                        code_type = "function"
                    
                    self.memory.store_code_artifact(
                        session_id=session_id,
                        file_path=relative_path,
                        content=content,
                        code_type=code_type
                    )
                    
                    self._processed_files.add(str(file_path))
                    logger.info(f"📦 Artefacto almacenado: {relative_path}")
                    
                except Exception as e:
                    logger.error(f"Error procesando {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Error escaneando artefactos: {e}")

    def reset(self):
        """Reinicia el conjunto de archivos procesados."""
        self._processed_files.clear()
