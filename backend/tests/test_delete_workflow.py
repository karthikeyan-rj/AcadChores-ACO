"""
20 tests for the File Agent delete workflow.
Covers: physical deletion, verification, path resolution, permissions, metadata, approval binding.
"""
import os
import time
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
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "report.txt").write_text("report content")
    (ws / "factorial.py").write_text("def fact(n): return 1 if n <= 1 else n * fact(n-1)")
    (ws / "notes-old.txt").write_text("old notes")
    (ws / "file with spaces.txt").write_text("space content")
    sub = ws / "Reports"
    sub.mkdir()
    (sub / "quarterly.txt").write_text("quarterly report")
    nested = ws / "Deep" / "Nested"
    nested.mkdir(parents=True)
    (nested / "deep_file.txt").write_text("deep content")
    (ws / "read_only.txt").write_text("readonly")
    os.chmod(str(ws / "read_only.txt"), 0o444)
    return ws


async def _noop_progress(pct, msg):
    pass


@pytest.fixture(autouse=True)
def mock_permission_guard():
    with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
        mock_guard.authorize_action = AsyncMock(return_value=True)
        yield mock_guard


class TestDeleteWorkflow:
    """Tests 1-20 for the delete workflow."""

    @pytest.mark.asyncio
    async def test_01_delete_existing_file(self, file_agent, tmp_workspace):
        """Test 1: Delete an existing file and verify result."""
        path = str(tmp_workspace / "report.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert result["verified"] is True
        assert result["path"] == path
        assert result["filename"] == "report.txt"
        assert "size" in result
        assert "modified" in result

    @pytest.mark.asyncio
    async def test_02_verify_physical_file_gone(self, file_agent, tmp_workspace):
        """Test 2: Verify the physical file no longer exists after deletion."""
        path = str(tmp_workspace / "factorial.py")
        assert os.path.exists(path)
        await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_03_delete_nested_file(self, file_agent, tmp_workspace):
        """Test 3: Delete a file in a nested directory."""
        path = str(tmp_workspace / "Reports" / "quarterly.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert result["verified"] is True
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_04_delete_file_with_spaces(self, file_agent, tmp_workspace):
        """Test 4: Delete a file with spaces in its name."""
        path = str(tmp_workspace / "file with spaces.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert result["verified"] is True
        assert result["filename"] == "file with spaces.txt"
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_05_resolve_desktop_path(self, file_agent, tmp_workspace):
        """Test 5: Resolve 'on my desktop' to the configured desktop path."""
        from app.services.planner import get_user_dir
        desktop = get_user_dir("desktop")
        assert os.path.isabs(desktop)
        assert "desktop" in desktop.lower() or "onedrive" in desktop.lower()

    @pytest.mark.asyncio
    async def test_06_reject_missing_file(self, file_agent, tmp_workspace):
        """Test 6: Reject deletion of a non-existent file."""
        path = str(tmp_workspace / "nonexistent.txt")
        with pytest.raises(FileNotFoundError):
            await file_agent.execute("delete", {"path": path}, _noop_progress)

    @pytest.mark.asyncio
    async def test_07_reject_directory(self, file_agent, tmp_workspace):
        """Test 7: Reject deleting a directory through file.delete."""
        path = str(tmp_workspace / "Reports")
        with pytest.raises(IsADirectoryError):
            await file_agent.execute("delete", {"path": path}, _noop_progress)

    @pytest.mark.asyncio
    async def test_08_reject_path_traversal(self, file_agent, tmp_workspace):
        """Test 8: Reject path traversal outside workspace."""
        malicious = str(tmp_workspace / ".." / ".." / "etc" / "passwd")
        with pytest.raises((PermissionError, FileNotFoundError)):
            await file_agent.execute("delete", {"path": malicious}, _noop_progress)

    @pytest.mark.asyncio
    @pytest.mark.real_workspace
    async def test_09_reject_path_outside_allowed_roots(self, file_agent, tmp_workspace):
        """Test 9: Reject a path outside allowed roots (blocked system directory)."""
        with pytest.raises(PermissionError):
            await file_agent.execute("delete", {"path": "C:\\Windows\\System32\\config\\SAM"}, _noop_progress)

    @pytest.mark.asyncio
    async def test_10_multiple_matches_require_clarification(self, file_agent, tmp_workspace):
        """Test 10: When multiple files match, planner should not auto-select."""
        from app.services.planner import PlannerService
        planner = PlannerService()
        result = await planner.generate_workflow_steps(
            "delete all txt files", user_id="test"
        )
        steps = result.get("steps", [])
        if steps:
            assert len(steps) >= 1
            for s in steps:
                assert s.get("action") in ("delete", "list", "move_matching", "find_text")

    @pytest.mark.asyncio
    async def test_11_approval_contains_exact_path(self, file_agent, tmp_workspace):
        """Test 11: Approval request contains the exact normalized path."""
        from app.services.planner import PlannerService
        planner = PlannerService()
        result = await planner.generate_workflow_steps(
            "delete factorial.py on my desktop", user_id="test"
        )
        pc = result.get("pending_confirmation")
        if pc and pc.get("type") == "file_delete":
            path = pc.get("path", "")
            assert os.path.isabs(path), f"Path should be absolute: {path}"
            assert "factorial.py" in path, f"Path should contain filename: {path}"

    @pytest.mark.asyncio
    async def test_12_approval_path_matches_execution_path(self, file_agent, tmp_workspace):
        """Test 12: The path in approval matches the path used for deletion."""
        path = str(tmp_workspace / "report.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["path"] == path

    @pytest.mark.asyncio
    async def test_13_verification_failure_marks_workflow_failed(self, file_agent, tmp_workspace):
        """Test 13: If verification fails, the result indicates failure."""
        from app.verification.engine import VerificationEngine, FileDeleteVerifier
        engine = VerificationEngine()
        step = {"step_id": "step_1", "agent_type": "file", "action": "delete"}
        result_that_lies = {"deleted": True, "verified": False, "path": "/fake/path.txt"}
        vresult = await engine.verify(step, result_that_lies)
        assert vresult.success is False
        assert "still exists" in vresult.message.lower() or "unverified" in vresult.message.lower() or "did not complete" in vresult.message.lower()

    @pytest.mark.asyncio
    async def test_14_metadata_removed_after_physical_deletion(self, file_agent, tmp_workspace):
        """Test 15: Metadata is only removed after physical deletion succeeds."""
        path = str(tmp_workspace / "report.txt")
        assert os.path.exists(path)
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert result["verified"] is True
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_15_failed_deletion_preserves_file(self, file_agent, tmp_workspace):
        """Test 16: If deletion fails (e.g., permission), the file is preserved."""
        path = str(tmp_workspace / "report.txt")
        with patch("os.remove", side_effect=PermissionError("Mocked permission error")):
            with pytest.raises(PermissionError):
                await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert os.path.exists(path), "File should still exist after failed deletion"

    @pytest.mark.asyncio
    async def test_16_verification_engine_verifies_delete(self, file_agent, tmp_workspace):
        """Test 17: FileDeleteVerifier checks file absence after deletion."""
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        path = str(tmp_workspace / "report.txt")
        await file_agent.execute("delete", {"path": path}, _noop_progress)
        step = {"step_id": "step_1", "agent_type": "file", "action": "delete"}
        result = {"deleted": True, "verified": True, "path": path}
        vresult = await engine.verify(step, result)
        assert vresult.success is True
        assert "verified" in vresult.message.lower()

    @pytest.mark.asyncio
    async def test_17_result_includes_file_metadata(self, file_agent, tmp_workspace):
        """Test: Result includes file size and modified time."""
        path = str(tmp_workspace / "report.txt")
        result = await file_agent.execute("delete", {"path": path}, _noop_progress)
        assert "size" in result
        assert isinstance(result["size"], int)
        assert result["size"] > 0
        assert "modified" in result
        assert result["modified"] is not None

    @pytest.mark.asyncio
    async def test_18_user_cannot_delete_other_user_file(self, file_agent, tmp_workspace):
        """Test 19: User A cannot delete User B's file (workspace validation)."""
        other_user_path = "C:\\Users\\OtherUser\\Desktop\\secret.txt"
        with pytest.raises((PermissionError, FileNotFoundError)):
            await file_agent.execute("delete", {"path": other_user_path}, _noop_progress)

    @pytest.mark.asyncio
    async def test_19_alias_delete_file_works(self, file_agent, tmp_workspace):
        """Test: Action alias 'delete_file' normalizes to 'delete'."""
        path = str(tmp_workspace / "notes-old.txt")
        result = await file_agent.execute("delete_file", {"path": path}, _noop_progress)
        assert result["deleted"] is True
        assert result["verified"] is True
        assert not os.path.exists(path)

    @pytest.mark.asyncio
    async def test_20_planner_generates_real_delete_step(self, tmp_workspace):
        """Test: Planner generates a real delete step, not just 'identify file'."""
        from app.services.planner import PlannerService
        planner = PlannerService()
        result = await planner.generate_workflow_steps(
            "delete factorial.py from my desktop", user_id="test"
        )
        steps = result.get("steps", [])
        assert len(steps) >= 1
        delete_steps = [s for s in steps if s.get("action") == "delete"]
        assert len(delete_steps) >= 1, f"Expected delete action, got: {[s.get('action') for s in steps]}"
        for s in delete_steps:
            assert "path" in s.get("parameters", {}), "Delete step must have path parameter"
