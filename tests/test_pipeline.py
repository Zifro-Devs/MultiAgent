"""Smoke & unit tests for the DevTeam AI pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ═══════════════════════════════════════════════════════════════════
# Settings
# ═══════════════════════════════════════════════════════════════════


class TestSettings:
    """Configuration loads without errors and has sane defaults."""

    def test_defaults(self):
        from src.config.settings import Settings

        s = Settings()
        assert s.app_name == "DevTeam AI"
        assert s.llm_provider == "ollama"
        assert s.artifacts_dir == "artifacts"
        assert s.debug is False

    def test_project_root_is_directory(self):
        from src.config.settings import Settings

        s = Settings()
        assert s.project_root.is_dir()

    def test_get_model_unknown_provider_raises(self):
        from src.config.settings import get_model

        with pytest.raises(ValueError, match="Unsupported"):
            get_model(provider="nonexistent", model_id="x")


# ═══════════════════════════════════════════════════════════════════
# Artifact Tools — security & functionality
# ═══════════════════════════════════════════════════════════════════


class _FakeRunContext:
    """Minimal stand-in for ``agno.run.RunContext``."""
    pass


class TestArtifactToolsSecurity:
    """Path-traversal and other safety checks."""

    def test_block_double_dot(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()
        result = json.loads(tools.write_file(rc, "../../../etc/passwd", "bad"))
        assert result["ok"] is False

    def test_block_absolute_path(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()
        result = json.loads(tools.write_file(rc, "/etc/shadow", "bad"))
        assert result["ok"] is False

    def test_block_dot_dot_in_middle(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()
        result = json.loads(tools.write_file(rc, "src/../../../etc/hosts", "bad"))
        assert result["ok"] is False

    def test_block_oversized_content(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()
        huge = "x" * 600_000
        result = json.loads(tools.write_file(rc, "big.txt", huge))
        assert result["ok"] is False


class TestArtifactToolsFunctionality:
    """Happy-path read / write / list operations."""

    def test_write_and_read(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()

        write_res = json.loads(tools.write_file(rc, "hello.py", "print('hi')"))
        assert write_res["ok"] is True
        assert write_res["path"] == "hello.py"

        content = tools.read_file(rc, "hello.py")
        assert content == "print('hi')"

    def test_write_nested_path(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()

        res = json.loads(tools.write_file(rc, "src/models/user.py", "class User: pass"))
        assert res["ok"] is True
        assert (tmp_path / "src" / "models" / "user.py").is_file()

    def test_list_files(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()

        tools.write_file(rc, "a.py", "a")
        tools.write_file(rc, "sub/b.py", "b")

        listing = json.loads(tools.list_files(rc))
        assert listing["ok"] is True
        assert listing["count"] == 2
        assert "a.py" in listing["files"]
        assert "sub/b.py" in listing["files"]

    def test_read_nonexistent_file(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()

        result = json.loads(tools.read_file(rc, "nope.py"))
        assert result["ok"] is False

    def test_list_nonexistent_subdir(self, tmp_path: Path):
        from src.tools.artifact_tools import ArtifactTools

        tools = ArtifactTools(str(tmp_path))
        rc = _FakeRunContext()

        result = json.loads(tools.list_files(rc, subdir="ghost"))
        assert result["ok"] is False


# ═══════════════════════════════════════════════════════════════════
# Database adapter
# ═══════════════════════════════════════════════════════════════════


class TestDatabase:
    """Database factory returns a valid backend."""

    def test_sqlite_fallback(self, tmp_path: Path):
        from src.config.settings import Settings
        from src.storage.database import get_database

        s = Settings(supabase_db_url="", artifacts_dir=str(tmp_path / "art"))
        db = get_database(s)
        # Should be a SqliteDb instance (fallback)
        assert db is not None


# ═══════════════════════════════════════════════════════════════════
# Team assembly (requires API key)
# ═══════════════════════════════════════════════════════════════════


class TestTeamAssembly:
    """Integracion: el equipo se construye sin errores."""

    def test_create_dev_team(self):
        from src.orchestrator.team import create_dev_team

        team = create_dev_team()
        assert team.name == "DevTeam AI"
        assert len(team.members) == 4
        # Verificar nombres en espanol
        names = {m.name for m in team.members}
        assert "Agente de Analisis" in names
        assert "Agente de Diseno" in names
        assert "Agente de Implementacion" in names
        assert "Agente de Validacion" in names
