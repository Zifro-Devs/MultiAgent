"""Secure file-system toolkit for project artifact management.

All I/O is sandboxed to a single root directory.  Path-traversal attacks
are blocked before any file operation executes.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path, PurePosixPath
from typing import Optional

from agno.run import RunContext
from agno.tools import Toolkit

logger = logging.getLogger(__name__)


class ArtifactTools(Toolkit):
    """Read / write / list source-code files inside a sandboxed directory.

    Security guarantees:
    * Relative paths only — absolute paths are rejected.
    * ``..`` segments are rejected.
    * The resolved path MUST remain under ``_root``.
    * File size is capped at ``_MAX_BYTES``.
    """

    _MAX_BYTES: int = 500_000  # 500 KB per file

    def __init__(self, artifacts_dir: str = "artifacts") -> None:
        self._root = Path(artifacts_dir).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        super().__init__(
            name="artifact_tools",
            instructions=(
                "Use these tools to create, read, and list project source-code "
                "files.  All paths are relative to the project root directory "
                "(e.g. 'src/main.py', 'tests/test_app.py')."
            ),
            tools=[self.write_file, self.read_file, self.list_files],
        )

    # ── Internal helpers ────────────────────────────────────────

    def _safe_resolve(self, relative_path: str) -> Path:
        """Resolve *relative_path* inside the sandbox or raise."""
        parts = PurePosixPath(relative_path).parts
        if not parts:
            raise ValueError("empty path")
        if ".." in parts:
            raise ValueError("'..' segments are not allowed")
        if PurePosixPath(relative_path).is_absolute():
            raise ValueError("absolute paths are not allowed")
        resolved = (self._root / "/".join(parts)).resolve()
        if not resolved.is_relative_to(self._root):
            raise ValueError("path escapes the sandbox")
        return resolved

    @staticmethod
    def _ok(payload: dict) -> str:
        return json.dumps({**payload, "ok": True}, ensure_ascii=False)

    @staticmethod
    def _err(message: str) -> str:
        return json.dumps({"ok": False, "error": message}, ensure_ascii=False)

    # ── Public tools (exposed to agents) ────────────────────────

    def write_file(
        self, run_context: RunContext, path: str, content: str
    ) -> str:
        """Create or overwrite a source-code file in the project.

        Args:
            path: Relative file path (e.g. ``src/main.py``).
            content: Complete text content to write.

        Returns:
            JSON confirmation with byte count, or an error object.
        """
        # El LLM a veces envía \n, \t como escapes literales en lugar de caracteres reales
        if "\\n" in content and "\n" not in content:
            content = content.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "")

        byte_len = len(content.encode("utf-8"))
        if byte_len > self._MAX_BYTES:
            return self._err(f"content exceeds {self._MAX_BYTES} bytes ({byte_len})")
        try:
            target = self._safe_resolve(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.debug("write_file  %s  (%d bytes)", path, byte_len)
            return self._ok({"path": path, "bytes": byte_len})
        except (ValueError, OSError) as exc:
            logger.warning("write_file blocked: %s → %s", path, exc)
            return self._err(str(exc))

    def read_file(self, run_context: RunContext, path: str) -> str:
        """Read a source-code file from the project.

        Args:
            path: Relative file path.

        Returns:
            The raw file content, or a JSON error object.
        """
        try:
            target = self._safe_resolve(path)
            if not target.is_file():
                return self._err(f"file not found: {path}")
            logger.debug("read_file   %s", path)
            return target.read_text(encoding="utf-8")
        except (ValueError, OSError) as exc:
            logger.warning("read_file blocked: %s → %s", path, exc)
            return self._err(str(exc))

    def list_files(
        self, run_context: RunContext, subdir: Optional[str] = None
    ) -> str:
        """List all files in the project directory (or a sub-directory).

        Args:
            subdir: Optional sub-directory to scope the listing.

        Returns:
            JSON with a ``files`` array and ``count``.
        """
        try:
            base = self._root if subdir is None else self._safe_resolve(subdir)
            if not base.is_dir():
                return self._err("directory not found")
            files = sorted(
                str(f.relative_to(self._root)).replace("\\", "/")
                for f in base.rglob("*")
                if f.is_file()
            )
            logger.debug("list_files  %s  (%d entries)", subdir or "/", len(files))
            return self._ok({"files": files, "count": len(files)})
        except (ValueError, OSError) as exc:
            logger.warning("list_files blocked: %s → %s", subdir, exc)
            return self._err(str(exc))
