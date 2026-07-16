"""Regression tests for the reliability pass (§3, §4, §8).

Covers:
  - Planner step sanitizer (§3)
  - Structured error suggestions (§4)
  - New file operation verifiers (§8)
  - Workflow validator edge cases
  - Intent classifier edge cases
"""
import pytest
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# §3: Planner step sanitizer
# ---------------------------------------------------------------------------

class TestPlannerSanitizer:
    """Test PlannerService._sanitize_steps static logic."""

    def _get_sanitizer(self):
        from app.services.planner import PlannerService
        svc = PlannerService.__new__(PlannerService)
        return svc._sanitize_steps

    def test_normalizes_filesystem_alias(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "filesystem", "action": "read", "parameters": {"path": "/tmp/a.txt"}}]
        result = sanitize(steps)
        assert len(result) == 1
        assert result[0]["agent_type"] == "file"

    def test_normalizes_browser_agent_alias(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "browser_agent", "action": "navigate", "parameters": {"url": "https://example.com"}}]
        result = sanitize(steps)
        assert result[0]["agent_type"] == "browser"

    def test_normalizes_file_system_agent_alias(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "file_system_agent", "action": "list", "parameters": {}}]
        result = sanitize(steps)
        assert result[0]["agent_type"] == "file"

    def test_drops_vague_actions(self):
        sanitize = self._get_sanitizer()
        steps = [
            {"agent_type": "file", "action": "read", "parameters": {"path": "/tmp/a.txt"}},
            {"agent_type": "file", "action": "handle", "parameters": {}},
            {"agent_type": "terminal", "action": "do_something", "parameters": {"command": "echo hi"}},
        ]
        result = sanitize(steps)
        assert len(result) == 1
        assert result[0]["action"] == "read"

    def test_drops_unknown_agent_type(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "alien_bot", "action": "beam", "parameters": {}}]
        result = sanitize(steps)
        assert len(result) == 0

    def test_drops_invalid_action_for_agent(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "terminal", "action": "navigate", "parameters": {"url": "https://x.com"}}]
        result = sanitize(steps)
        assert len(result) == 0

    def test_fills_missing_step_id_and_name(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "file", "action": "read", "parameters": {"path": "/tmp/a.txt"}}]
        result = sanitize(steps)
        assert result[0]["step_id"] == "step_1"
        assert result[0]["name"] == "read"

    def test_renames_params_to_parameters(self):
        sanitize = self._get_sanitizer()
        steps = [{"agent_type": "terminal", "action": "run", "params": {"command": "ls"}}]
        result = sanitize(steps)
        assert "parameters" in result[0]
        assert result[0]["parameters"]["command"] == "ls"
        assert "params" not in result[0]

    def test_empty_input_returns_empty(self):
        sanitize = self._get_sanitizer()
        assert sanitize([]) == []

    def test_mixed_valid_and_invalid(self):
        sanitize = self._get_sanitizer()
        steps = [
            {"agent_type": "file", "action": "read", "parameters": {"path": "/tmp/a.txt"}},
            {"agent_type": "file", "action": "process", "parameters": {}},
            {"agent_type": "browser", "action": "navigate", "parameters": {"url": "https://x.com"}},
        ]
        result = sanitize(steps)
        assert len(result) == 2
        assert result[0]["action"] == "read"
        assert result[1]["action"] == "navigate"


# ---------------------------------------------------------------------------
# §4: Structured error suggestions
# ---------------------------------------------------------------------------

class TestErrorSuggestions:
    """Test _get_error_suggestion helper."""

    def _suggest(self, error_type, error_msg, step_data=None):
        from app.services.worker import _get_error_suggestion
        return _get_error_suggestion(error_type, error_msg, step_data or {})

    def test_permission_error_suggestion(self):
        msg = self._suggest("PermissionError", "denied")
        assert "permission" in msg.lower()

    def test_file_not_found_suggestion(self):
        msg = self._suggest("FileNotFoundError", "not found", {"agent_type": "file", "parameters": {"path": "/tmp/missing.txt"}})
        assert "/tmp/missing.txt" in msg

    def test_file_exists_suggestion(self):
        msg = self._suggest("FileExistsError", "already exists")
        assert "already exists" in msg

    def test_timeout_suggestion(self):
        msg = self._suggest("TimeoutError", "timed out", {"agent_type": "browser"})
        assert "browser" in msg.lower()

    def test_runtime_error_click_suggestion(self):
        msg = self._suggest("RuntimeError", "Could not click any element")
        assert "element" in msg.lower()

    def test_runtime_error_navigate_suggestion(self):
        msg = self._suggest("RuntimeError", "Failed to navigate to https://x.com")
        assert "navigation" in msg.lower() or "url" in msg.lower()

    def test_unknown_error_suggestion(self):
        msg = self._suggest("RuntimeError", "some random error", {"agent_type": "terminal", "action": "run"})
        assert "terminal" in msg
        assert "run" in msg

    def test_asyncio_timeout_suggestion(self):
        msg = self._suggest("asyncio.TimeoutError", "timed out", {"agent_type": "browser"})
        assert "browser" in msg.lower()

    def test_os_error_suggestion(self):
        msg = self._suggest("OSError", "permission denied")
        assert "permission" in msg.lower() or "file system" in msg.lower()

    def test_value_error_suggestion(self):
        msg = self._suggest("ValueError", "invalid value", {"agent_type": "file", "action": "write"})
        assert "file" in msg
        assert "write" in msg


# ---------------------------------------------------------------------------
# §8: Verification engine — new file verifiers
# ---------------------------------------------------------------------------

class TestFileVerifiers:
    """Test the new file operation verifiers in VerificationEngine."""

    @pytest.fixture
    def engine(self):
        from app.verification.engine import VerificationEngine
        return VerificationEngine()

    @pytest.mark.asyncio
    async def test_file_move_verifier_success(self, engine):
        step = {"agent_type": "file", "action": "move", "step_id": "s1"}
        result = {"moved": True, "success": True, "source": "/tmp/a.txt", "destination": "/tmp/b.txt"}
        vr = await engine.verify(step, result)
        assert vr.success is True

    @pytest.mark.asyncio
    async def test_file_rename_verifier_success(self, engine):
        step = {"agent_type": "file", "action": "rename", "step_id": "s1"}
        result = {"renamed": True, "success": True, "old_path": "/tmp/old.txt", "new_path": "/tmp/new.txt"}
        vr = await engine.verify(step, result)
        assert vr.success is True

    @pytest.mark.asyncio
    async def test_file_copy_verifier_success(self, engine):
        step = {"agent_type": "file", "action": "copy", "step_id": "s1"}
        result = {"copied": True, "success": True, "source": "/tmp/a.txt", "destination": "/tmp/b.txt"}
        vr = await engine.verify(step, result)
        assert vr.success is True

    @pytest.mark.asyncio
    async def test_file_create_directory_verifier_success(self, engine):
        step = {"agent_type": "file", "action": "create_directory", "step_id": "s1"}
        result = {"success": True, "path": "/tmp/newdir", "created": True}
        vr = await engine.verify(step, result)
        assert vr.success is True

    @pytest.mark.asyncio
    async def test_file_find_text_verifier_with_matches(self, engine):
        step = {"agent_type": "file", "action": "find_text", "step_id": "s1"}
        result = {"match_count": 5, "query": "hello", "matches": []}
        vr = await engine.verify(step, result)
        assert vr.success is True
        assert "5 match" in vr.message

    @pytest.mark.asyncio
    async def test_file_find_text_verifier_no_matches(self, engine):
        step = {"agent_type": "file", "action": "find_text", "step_id": "s1"}
        result = {"match_count": 0, "query": "nonexistent", "matches": []}
        vr = await engine.verify(step, result)
        assert vr.success is True
        assert vr.confidence < 1.0

    @pytest.mark.asyncio
    async def test_file_search_verifier(self, engine):
        step = {"agent_type": "file", "action": "search", "step_id": "s1"}
        result = {"match_count": 3, "query": "test", "matches": []}
        vr = await engine.verify(step, result)
        assert vr.success is True

    @pytest.mark.asyncio
    async def test_file_move_matching_verifier_success(self, engine):
        step = {"agent_type": "file", "action": "move_matching", "step_id": "s1"}
        result = {"success": True, "moved_count": 5, "matched_count": 5, "skipped": []}
        vr = await engine.verify(step, result)
        assert vr.success is True
        assert "5/5" in vr.message

    @pytest.mark.asyncio
    async def test_file_move_matching_verifier_none_matched(self, engine):
        step = {"agent_type": "file", "action": "move_matching", "step_id": "s1"}
        result = {"success": True, "moved_count": 0, "matched_count": 0, "skipped": []}
        vr = await engine.verify(step, result)
        assert vr.success is True
        assert "No matching" in vr.message

    @pytest.mark.asyncio
    async def test_file_move_verifier_failure(self, engine):
        step = {"agent_type": "file", "action": "move", "step_id": "s1"}
        result = {"moved": False, "success": False}
        vr = await engine.verify(step, result)
        assert vr.success is False
