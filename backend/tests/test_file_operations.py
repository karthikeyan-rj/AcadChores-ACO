"""
Tests for File Agent operations: delete, move, rename, copy, create_directory, move_matching.
"""
import os
import pytest
import tempfile
import shutil
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.agent_dispatcher import FileAgent, _is_path_blocked


@pytest.fixture
def file_agent():
    return FileAgent()


@pytest.fixture
def tmp_workspace(tmp_path):
    """Create a temporary workspace with test files."""
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "report.txt").write_text("report content")
    (ws / "notes-old.txt").write_text("old notes")
    (ws / "invoice_march.pdf").write_bytes(b"pdf-content")
    (ws / "invoice_april.pdf").write_bytes(b"pdf-content")
    (ws / "resume_final.docx").write_bytes(b"doc-content")
    (ws / "IMG_001.jpg").write_bytes(b"img-content")
    (ws / "IMG_002.jpg").write_bytes(b"img-content")
    (ws / "data.txt").write_text("some data")
    sub = ws / "Reports"
    sub.mkdir()
    (sub / "quarterly.txt").write_text("quarterly report")
    nested = ws / "Deep" / "Nested"
    nested.mkdir(parents=True)
    (nested / "deep_file.txt").write_text("deep content")
    return ws


async def _noop_progress(pct, msg):
    pass


@pytest.fixture(autouse=True)
def mock_permission_guard():
    """Mock permission guard to always allow actions in tests."""
    with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
        mock_guard.authorize_action = AsyncMock(return_value=True)
        yield mock_guard


class TestFileAgentDelete:
    @pytest.mark.asyncio
    async def test_delete_file(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "report.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_delete_nested_file(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "Reports" / "quarterly.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_delete_file_with_spaces(self, file_agent, tmp_workspace):
        spaced = tmp_workspace / "file with spaces.txt"
        spaced.write_text("content")
        result = await file_agent.execute("delete", {"path": str(spaced)}, _noop_progress)
        assert result["deleted"] is True
        assert not spaced.exists()

    @pytest.mark.asyncio
    async def test_delete_rejects_directory(self, file_agent, tmp_workspace):
        with pytest.raises(IsADirectoryError):
            await file_agent.execute("delete", {"path": str(tmp_workspace / "Reports")}, _noop_progress)

    @pytest.mark.asyncio
    async def test_delete_rejects_traversal(self, file_agent, tmp_workspace):
        with pytest.raises((PermissionError, FileNotFoundError)):
            await file_agent.execute("delete", {"path": str(tmp_workspace / ".." / ".." / "etc" / "passwd")}, _noop_progress)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises(self, file_agent, tmp_workspace):
        with pytest.raises(FileNotFoundError):
            await file_agent.execute("delete", {"path": str(tmp_workspace / "nope.txt")}, _noop_progress)

    @pytest.mark.asyncio
    async def test_delete_via_alias(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "data.txt")
        result = await file_agent.execute("delete_file", {"path": path}, _noop_progress)
        assert result["deleted"] is True


class TestFileAgentMove:
    @pytest.mark.asyncio
    async def test_move_file(self, file_agent, tmp_workspace):
        src = str(tmp_workspace / "report.txt")
        dst = str(tmp_workspace / "Reports" / "report.txt")
        result = await file_agent.execute("move", {"source": src, "destination": dst}, _noop_progress)
        assert result["moved"] is True
        assert not os.path.exists(src)
        assert os.path.exists(dst)

    @pytest.mark.asyncio
    async def test_move_creates_parent(self, file_agent, tmp_workspace):
        src = str(tmp_workspace / "data.txt")
        dst = str(tmp_workspace / "NewFolder" / "data.txt")
        result = await file_agent.execute("move", {"source": src, "destination": dst, "create_parent": True}, _noop_progress)
        assert result["moved"] is True
        assert os.path.exists(dst)

    @pytest.mark.asyncio
    async def test_move_rejects_overwrite(self, file_agent, tmp_workspace):
        src = str(tmp_workspace / "report.txt")
        dst = str(tmp_workspace / "Reports" / "quarterly.txt")
        with pytest.raises(FileExistsError):
            await file_agent.execute("move", {"source": src, "destination": dst}, _noop_progress)

    @pytest.mark.asyncio
    async def test_move_nonexistent_raises(self, file_agent, tmp_workspace):
        with pytest.raises(FileNotFoundError):
            await file_agent.execute("move", {
                "source": str(tmp_workspace / "nope.txt"),
                "destination": str(tmp_workspace / "Reports" / "nope.txt"),
            }, _noop_progress)


class TestFileAgentRename:
    @pytest.mark.asyncio
    async def test_rename_file(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "notes-old.txt")
        result = await file_agent.execute("rename", {"path": path, "new_name": "notes.txt"}, _noop_progress)
        assert result["renamed"] is True
        assert not os.path.exists(path)
        assert os.path.exists(result["new_path"])

    @pytest.mark.asyncio
    async def test_rename_rejects_duplicate(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "report.txt")
        with pytest.raises(FileExistsError):
            await file_agent.execute("rename", {"path": path, "new_name": "data.txt"}, _noop_progress)

    @pytest.mark.asyncio
    async def test_rename_empty_new_name_raises(self, file_agent, tmp_workspace):
        with pytest.raises(ValueError):
            await file_agent.execute("rename", {"path": str(tmp_workspace / "report.txt"), "new_name": ""}, _noop_progress)


class TestFileAgentCopy:
    @pytest.mark.asyncio
    async def test_copy_file(self, file_agent, tmp_workspace):
        src = str(tmp_workspace / "report.txt")
        dst = str(tmp_workspace / "Reports" / "report_copy.txt")
        result = await file_agent.execute("copy", {"source": src, "destination": dst}, _noop_progress)
        assert result["copied"] is True
        assert os.path.exists(src)
        assert os.path.exists(dst)

    @pytest.mark.asyncio
    async def test_copy_rejects_existing_dest(self, file_agent, tmp_workspace):
        src = str(tmp_workspace / "report.txt")
        dst = str(tmp_workspace / "data.txt")
        with pytest.raises(FileExistsError):
            await file_agent.execute("copy", {"source": src, "destination": dst}, _noop_progress)


class TestFileAgentCreateDirectory:
    @pytest.mark.asyncio
    async def test_create_directory(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "NewFolder")
        result = await file_agent.execute("create_directory", {"path": path}, _noop_progress)
        assert result["created"] is True
        assert os.path.isdir(path)

    @pytest.mark.asyncio
    async def test_create_directory_already_exists(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "Reports")
        result = await file_agent.execute("create_directory", {"path": path}, _noop_progress)
        assert result["success"] is True
        assert "already exists" in result.get("message", "")

    @pytest.mark.asyncio
    async def test_create_folder_alias(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "TestFolder")
        result = await file_agent.execute("create_folder", {"path": path}, _noop_progress)
        assert result["created"] is True


class TestFileAgentMoveMatching:
    @pytest.mark.asyncio
    async def test_move_by_keyword(self, file_agent, tmp_workspace):
        src_dir = str(tmp_workspace)
        dst_dir = str(tmp_workspace / "Invoices")
        result = await file_agent.execute("move_matching", {
            "source_directory": src_dir,
            "destination_directory": dst_dir,
            "match_type": "filename_contains",
            "keyword": "invoice",
            "case_sensitive": False,
            "create_destination": True,
        }, _noop_progress)
        assert result["matched_count"] == 2
        assert result["moved_count"] == 2
        assert os.path.isdir(dst_dir)
        for f in result["moved_files"]:
            assert os.path.exists(os.path.join(dst_dir, f))

    @pytest.mark.asyncio
    async def test_move_by_extension(self, file_agent, tmp_workspace):
        src_dir = str(tmp_workspace)
        dst_dir = str(tmp_workspace / "Images")
        result = await file_agent.execute("move_matching", {
            "source_directory": src_dir,
            "destination_directory": dst_dir,
            "match_type": "extension",
            "keyword": "jpg",
            "create_destination": True,
        }, _noop_progress)
        assert result["matched_count"] == 2
        assert result["moved_count"] == 2

    @pytest.mark.asyncio
    async def test_move_by_starts_with(self, file_agent, tmp_workspace):
        src_dir = str(tmp_workspace)
        dst_dir = str(tmp_workspace / "Images")
        result = await file_agent.execute("move_matching", {
            "source_directory": src_dir,
            "destination_directory": dst_dir,
            "match_type": "filename_starts_with",
            "keyword": "IMG_",
            "create_destination": True,
        }, _noop_progress)
        assert result["matched_count"] == 2
        assert result["moved_count"] == 2

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self, file_agent, tmp_workspace):
        (tmp_workspace / "RESUME_upper.txt").write_text("resume")
        src_dir = str(tmp_workspace)
        dst_dir = str(tmp_workspace / "Resumes")
        result = await file_agent.execute("move_matching", {
            "source_directory": src_dir,
            "destination_directory": dst_dir,
            "match_type": "filename_contains",
            "keyword": "resume",
            "case_sensitive": False,
            "create_destination": True,
        }, _noop_progress)
        assert result["matched_count"] >= 1

    @pytest.mark.asyncio
    async def test_existing_dest_not_overwritten(self, file_agent, tmp_workspace):
        dst_dir = tmp_workspace / "Invoices"
        dst_dir.mkdir()
        (dst_dir / "invoice_march.pdf").write_text("existing")
        result = await file_agent.execute("move_matching", {
            "source_directory": str(tmp_workspace),
            "destination_directory": str(dst_dir),
            "match_type": "filename_contains",
            "keyword": "invoice",
            "create_destination": True,
        }, _noop_progress)
        assert len(result["skipped"]) >= 1
        assert result["skipped"][0]["reason"] == "destination already exists"

    @pytest.mark.asyncio
    async def test_invalid_match_type_raises(self, file_agent, tmp_workspace):
        with pytest.raises(ValueError, match="Unsupported match_type"):
            await file_agent.execute("move_matching", {
                "source_directory": str(tmp_workspace),
                "destination_directory": str(tmp_workspace / "Out"),
                "match_type": "invalid_type",
                "keyword": "test",
            }, _noop_progress)


class TestFileAgentActionNormalization:
    @pytest.mark.asyncio
    async def test_alias_move_file(self, file_agent, tmp_workspace):
        src = str(tmp_workspace / "data.txt")
        dst = str(tmp_workspace / "Reports" / "data.txt")
        result = await file_agent.execute("move_file", {"source": src, "destination": dst}, _noop_progress)
        assert result["moved"] is True

    @pytest.mark.asyncio
    async def test_alias_rename_file(self, file_agent, tmp_workspace):
        path = str(tmp_workspace / "notes-old.txt")
        result = await file_agent.execute("rename_file", {"path": path, "new_name": "notes.txt"}, _noop_progress)
        assert result["renamed"] is True

    @pytest.mark.asyncio
    async def test_alias_move_files_by_keyword(self, file_agent, tmp_workspace):
        result = await file_agent.execute("move_files_by_keyword", {
            "source_directory": str(tmp_workspace),
            "destination_directory": str(tmp_workspace / "PDFs"),
            "match_type": "extension",
            "keyword": "pdf",
            "create_destination": True,
        }, _noop_progress)
        assert result["moved_count"] == 2


class TestFileAgentUnknownAction:
    @pytest.mark.asyncio
    async def test_unknown_action_raises(self, file_agent, tmp_workspace):
        with pytest.raises(ValueError, match="Unknown file action"):
            await file_agent.execute("nonexistent_action", {}, _noop_progress)


class TestCrossUserWorkspace:
    @pytest.mark.asyncio
    async def test_blocked_system_path(self, file_agent):
        with pytest.raises(PermissionError):
            await file_agent.execute("delete", {"path": "C:\\Windows\\test.txt"}, _noop_progress)
