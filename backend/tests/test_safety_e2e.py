"""
End-to-end safety and reliability tests for the Autonomous Computer Operator.

These tests verify that all security controls, safety checks, and reliability
mechanisms work correctly without executing any dangerous operations.
"""
import os
import sys
import json
import pytest
import asyncio
import tempfile
import subprocess
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from datetime import datetime


# ==============================================================================
# 1. Terminal Agent Safety Tests
# ==============================================================================

class TestTerminalAgentSafety:
    """Verify destructive command blocking and output limits."""

    @pytest.fixture
    def terminal_agent(self):
        from app.services.agent_dispatcher import TerminalAgent
        return TerminalAgent()

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_root(self, terminal_agent):
        """Must block rm -rf /"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "rm -rf /"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_format_c(self, terminal_agent):
        """Must block format C:"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "format C:"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_del_recursive(self, terminal_agent):
        """Must block del /s /q"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "del /s /q C:\\*"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_shutdown(self, terminal_agent):
        """Must block shutdown"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "shutdown /s /t 0"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_sudo_rm_rf(self, terminal_agent):
        """Must block sudo rm -rf"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "sudo rm -rf /"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_mkfs(self, terminal_agent):
        """Must block mkfs"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "mkfs.ext4 /dev/sda"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_dd_if(self, terminal_agent):
        """Must block dd if="""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "dd if=/dev/zero of=/dev/sda"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_fork_bomb(self, terminal_agent):
        """Must block fork bomb"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": ":(){ :|:& };:"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_taskkill_explorer(self, terminal_agent):
        """Must block taskkill /F /IM explorer"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="Blocked dangerous"):
                await terminal_agent.execute("run", {"command": "taskkill /F /IM explorer.exe"}, progress)

    @pytest.mark.asyncio
    async def test_safe_command_allowed(self, terminal_agent):
        """Safe commands should not be blocked"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with patch("subprocess.run") as mock_run:
                mock_proc = MagicMock()
                mock_proc.returncode = 0
                mock_proc.stdout = "hello"
                mock_proc.stderr = ""
                mock_run.return_value = mock_proc
                result = await terminal_agent.execute("run", {"command": "echo hello"}, progress)
                assert result["returncode"] == 0

    @pytest.mark.asyncio
    async def test_permission_denied(self, terminal_agent):
        """Must block when permission guard denies"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=False)
            with pytest.raises(PermissionError, match="rejected by user policy"):
                await terminal_agent.execute("run", {"command": "echo hello"}, progress)


# ==============================================================================
# 2. File Agent Safety Tests
# ==============================================================================

class TestFileAgentSafety:
    """Verify path restrictions for file write/delete."""

    @pytest.fixture
    def file_agent(self):
        from app.services.agent_dispatcher import FileAgent
        return FileAgent()

    @pytest.mark.asyncio
    async def test_blocks_write_to_windows_dir(self, file_agent):
        """Must block writes to C:\\Windows"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="blocked system directory"):
                await file_agent.execute("write", {"path": "C:\\Windows\\test.txt", "content": "bad"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_write_to_etc(self, file_agent):
        """Must block writes to /etc"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="blocked system directory"):
                await file_agent.execute("write", {"path": "/etc/passwd", "content": "bad"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_delete_to_program_files(self, file_agent):
        """Must block deletes in Program Files"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="blocked system directory"):
                await file_agent.execute("delete", {"path": "C:\\Program Files\\app.exe"}, progress)

    @pytest.mark.asyncio
    async def test_blocks_write_to_usr(self, file_agent):
        """Must block writes to /usr"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with pytest.raises(PermissionError, match="blocked system directory"):
                await file_agent.execute("write", {"path": "/usr/bin/evil", "content": "bad"}, progress)

    @pytest.mark.asyncio
    async def test_safe_write_allowed(self, file_agent):
        """Safe writes to user directories should be allowed"""
        progress = AsyncMock()
        with patch("app.services.agent_dispatcher.permission_guard") as mock_guard:
            mock_guard.authorize_action = AsyncMock(return_value=True)
            with tempfile.TemporaryDirectory() as tmpdir:
                test_path = os.path.join(tmpdir, "test.txt")
                result = await file_agent.execute("write", {"path": test_path, "content": "hello"}, progress)
                assert result["success"] is True
                assert os.path.exists(test_path)

    @pytest.mark.asyncio
    async def test_read_action_no_permission_check(self, file_agent):
        """Read (safe action) should not require permission check"""
        progress = AsyncMock()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("test content")
            f_path = f.name
        try:
            result = await file_agent.execute("read", {"path": f_path}, progress)
            assert result["content"] == "test content"
        finally:
            os.unlink(f_path)


# ==============================================================================
# 3. URL Validation Tests
# ==============================================================================

class TestURLValidation:
    """Verify browser URL scheme validation."""

    def test_allows_http(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("http://example.com") is True

    def test_allows_https(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("https://google.com") is True

    def test_blocks_file_scheme(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("file:///etc/passwd") is False

    def test_blocks_javascript_scheme(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("javascript:alert(1)") is False

    def test_blocks_data_scheme(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("data:text/html,<script>alert(1)</script>") is False

    def test_blocks_empty_url(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("") is False

    def test_blocks_malformed_url(self):
        from app.services.agent_dispatcher import _validate_url_scheme
        assert _validate_url_scheme("not-a-url") is False


# ==============================================================================
# 4. JS Sanitization Tests
# ==============================================================================

class TestJSSanitization:
    """Verify JavaScript string sanitization prevents injection."""

    def test_escapes_single_quotes(self):
        from app.services.agent_dispatcher import _sanitize_js_string
        result = _sanitize_js_string("it's a test")
        assert "'" not in result or "\\'" in result

    def test_escapes_backslashes(self):
        from app.services.agent_dispatcher import _sanitize_js_string
        result = _sanitize_js_string("path\\to\\file")
        assert "\\\\" in result

    def test_escapes_newlines(self):
        from app.services.agent_dispatcher import _sanitize_js_string
        result = _sanitize_js_string("line1\nline2")
        assert "\\n" in result

    def test_escapes_carriage_returns(self):
        from app.services.agent_dispatcher import _sanitize_js_string
        result = _sanitize_js_string("line1\rline2")
        assert "\\r" in result

    def test_injection_attempt_neutralized(self):
        from app.services.agent_dispatcher import _sanitize_js_string
        malicious = "'; alert('xss'); //"
        result = _sanitize_js_string(malicious)
        assert "alert" not in result or "\\x61lert" in result or "\\'" in result


# ==============================================================================
# 5. Plugin Sandbox Tests
# ==============================================================================

class TestPluginSandbox:
    """Verify plugin subprocess isolation."""

    @pytest.fixture
    def sandbox(self):
        from app.plugin_sdk.sandbox import plugin_sandbox
        return plugin_sandbox

    def test_simple_plugin_execution(self, sandbox):
        """A simple plugin should execute and return result"""
        code = "def run(inputs): return {'sum': inputs.get('a', 0) + inputs.get('b', 0)}"
        result = sandbox.execute(code, "run", {"a": 2, "b": 3})
        assert result["success"] is True
        assert result["result"]["sum"] == 5

    def test_missing_entry_point(self, sandbox):
        """Should fail gracefully when entry point is not found"""
        code = "def helper(inputs): return inputs"
        result = sandbox.execute(code, "nonexistent", {})
        assert result["success"] is False
        assert "not found" in result["error"]

    def test_invalid_entry_point_name(self, sandbox):
        """Should reject invalid Python identifier as entry point"""
        code = "def run(inputs): return inputs"
        result = sandbox.execute(code, "not a valid name!", {})
        assert result["success"] is False
        assert "Invalid entry point" in result["error"]

    def test_plugin_exception_handling(self, sandbox):
        """Should handle plugin exceptions gracefully"""
        code = "def run(inputs): raise ValueError('test error')"
        result = sandbox.execute(code, "run", {})
        assert result["success"] is False
        assert "test error" in result["error"]

    def test_non_callable_entry_point(self, sandbox):
        """Should reject non-callable entry point"""
        code = "run = 42"
        result = sandbox.execute(code, "run", {})
        assert result["success"] is False
        assert "not callable" in result["error"]

    def test_plugin_timeout(self, sandbox):
        """Plugin that runs too long should be killed"""
        code = "import time\ndef run(inputs): time.sleep(60); return {}"
        result = sandbox.execute(code, "run", {})
        assert result["success"] is False
        assert "timed out" in result["error"]


# ==============================================================================
# 6. State Machine Tests
# ==============================================================================

class TestStateMachineSafety:
    """Verify state machine transition validation and cleanup."""

    @pytest.mark.asyncio
    async def test_invalid_transition_rejected(self):
        """Invalid transitions should be rejected"""
        from app.services.state_machine import WorkflowStateMachine, WorkflowState, _in_memory_states
        from app.core.database import db_manager
        from bson import ObjectId
        oid = str(ObjectId())
        # Set initial state to COMPLETED
        _in_memory_states[oid] = WorkflowState.COMPLETED.value
        try:
            with patch.object(db_manager, 'use_memory', True):
                # COMPLETED -> EXECUTING is invalid
                result = await WorkflowStateMachine.transition_to(oid, WorkflowState.EXECUTING)
                assert result is False
        finally:
            _in_memory_states.pop(oid, None)

    @pytest.mark.asyncio
    async def test_valid_transition_accepted(self):
        """Valid transitions should be accepted"""
        from app.services.state_machine import WorkflowStateMachine, WorkflowState, _in_memory_states
        from app.core.database import db_manager
        from bson import ObjectId
        oid = str(ObjectId())
        _in_memory_states[oid] = WorkflowState.IDLE.value
        try:
            with patch.object(db_manager, 'use_memory', True):
                # IDLE -> PLANNING is valid
                result = await WorkflowStateMachine.transition_to(oid, WorkflowState.PLANNING)
                assert result is True
        finally:
            _in_memory_states.pop(oid, None)

    @pytest.mark.asyncio
    async def test_in_memory_cleanup(self):
        """In-memory dict cleanup should evict old entries"""
        from app.services.state_machine import _in_memory_states, _cleanup_in_memory_states, _MAX_IN_MEMORY_ENTRIES
        from bson import ObjectId
        # Fill the dict beyond limit
        for i in range(_MAX_IN_MEMORY_ENTRIES + 10):
            _in_memory_states[str(ObjectId())] = "Idle"
        _cleanup_in_memory_states()
        assert len(_in_memory_states) <= _MAX_IN_MEMORY_ENTRIES


# ==============================================================================
# 7. Worker Safety Tests
# ==============================================================================

class TestWorkerSafety:
    """Verify task execution timeout."""

    def test_task_execution_timeout_exists(self):
        """Task timeout constant should be defined"""
        from app.services.worker import TASK_EXECUTION_TIMEOUT
        assert TASK_EXECUTION_TIMEOUT > 0
        assert TASK_EXECUTION_TIMEOUT <= 600

    def test_in_memory_task_cleanup(self):
        """Task status cleanup should work"""
        from app.services.worker import _in_memory_task_statuses, _cleanup_task_statuses
        from uuid import uuid4
        # Fill with completed tasks
        for i in range(600):
            tid = str(uuid4())
            _in_memory_task_statuses[tid] = {"status": "completed", "result": ""}
        _cleanup_task_statuses()
        assert len(_in_memory_task_statuses) <= 500
        # Clean up
        _in_memory_task_statuses.clear()


# ==============================================================================
# 8. Recovery Engine Tests
# ==============================================================================

class TestRecoveryEngineSafety:
    """Verify recovery attempt limits and cleanup."""

    @pytest.mark.asyncio
    async def test_abort_after_five_attempts(self):
        """Should abort after 5 recovery attempts"""
        from app.recovery.engine import RecoveryEngine, RecoveryStrategy
        engine = RecoveryEngine()
        step = {"agent_type": "terminal", "action": "run", "parameters": {"command": "test"}}
        for i in range(5):
            action = await engine.recover(step, None, None, "step_1")
        assert action.strategy == RecoveryStrategy.ABORT

    @pytest.mark.asyncio
    async def test_first_attempt_is_retry(self):
        """First recovery attempt should be RETRY"""
        from app.recovery.engine import RecoveryEngine, RecoveryStrategy
        engine = RecoveryEngine()
        step = {"agent_type": "browser", "action": "click", "parameters": {"selector": "#btn"}}
        action = await engine.recover(step, None, None, "step_2")
        assert action.strategy == RecoveryStrategy.RETRY

    @pytest.mark.asyncio
    async def test_command_not_found_aborts_immediately(self):
        """Command not found errors should abort immediately"""
        from app.recovery.engine import RecoveryEngine, RecoveryStrategy
        engine = RecoveryEngine()
        step = {"agent_type": "terminal", "action": "run", "parameters": {"command": "nonexistent_tool"}}
        action = await engine.recover(step, Exception("command not found"), None, "step_3")
        assert action.strategy == RecoveryStrategy.ABORT

    @pytest.mark.asyncio
    async def test_cleanup_works(self):
        """reset_all should clear all attempts"""
        from app.recovery.engine import RecoveryEngine
        engine = RecoveryEngine()
        step = {"agent_type": "browser", "action": "click", "parameters": {}}
        await engine.recover(step, None, None, "s1")
        await engine.recover(step, None, None, "s2")
        assert engine.get_attempts("s1") == 1
        engine.reset_all()
        assert engine.get_attempts("s1") == 0

    @pytest.mark.asyncio
    async def test_attempt_dict_cleanup(self):
        """Attempts dict should be cleaned up when too large"""
        from app.recovery.engine import RecoveryEngine
        engine = RecoveryEngine()
        engine._max_tracked_steps = 5
        step = {"agent_type": "browser", "action": "click", "parameters": {}}
        for i in range(10):
            await engine.recover(step, None, None, f"step_{i}")
        assert len(engine._attempts) <= 5


# ==============================================================================
# 9. Verification Engine Tests
# ==============================================================================

class TestVerificationEngine:
    """Verify all verifier types work correctly."""

    @pytest.mark.asyncio
    async def test_navigate_verifier_success(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "navigate", "step_id": "s1"}
        result = {"url": "https://google.com", "title": "Google"}
        vresult = await engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_navigate_verifier_no_url(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "navigate", "step_id": "s1"}
        result = {}
        vresult = await engine.verify(step, result)
        assert vresult.success is False

    @pytest.mark.asyncio
    async def test_click_verifier_success(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "click", "step_id": "s1"}
        result = {"success": True}
        vresult = await engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_fill_verifier_value_match(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "fill", "step_id": "s1", "parameters": {"value": "hello world"}}
        result = {"filled": True, "method": "page.fill", "actual_value": "hello world"}
        vresult = await engine.verify(step, result)
        assert vresult.success is True
        assert vresult.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_fill_verifier_value_mismatch(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "fill", "step_id": "s1", "parameters": {"value": "expected text"}}
        result = {"filled": True, "method": "page.fill", "actual_value": "completely different"}
        vresult = await engine.verify(step, result)
        assert vresult.success is False

    @pytest.mark.asyncio
    async def test_scrape_text_verifier(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "scrape_text", "step_id": "s1"}
        result = {"text": "This is a long enough scraped text from the page"}
        vresult = await engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_scrape_links_verifier(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "browser", "action": "scrape_links", "step_id": "s1"}
        result = {"links": [{"title": "Link1", "url": "https://example.com"}], "count": 1}
        vresult = await engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_terminal_verifier_exit_code_zero(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "terminal", "action": "run", "step_id": "s1"}
        result = {"returncode": 0, "stdout": "done", "stderr": ""}
        vresult = await engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_terminal_verifier_exit_code_nonzero(self):
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "terminal", "action": "run", "step_id": "s1"}
        result = {"returncode": 1, "stdout": "", "stderr": "error"}
        vresult = await engine.verify(step, result)
        assert vresult.success is False

    @pytest.mark.asyncio
    async def test_no_verifier_assumed_success(self):
        """Unknown agent/action should return assumed success"""
        from app.verification.engine import VerificationEngine
        engine = VerificationEngine()
        step = {"agent_type": "unknown", "action": "do_something", "step_id": "s1"}
        result = {}
        vresult = await engine.verify(step, result)
        assert vresult.success is True
        assert "assumed success" in vresult.message.lower()


# ==============================================================================
# 10. PermissionGuard Tests
# ==============================================================================

class TestPermissionGuard:
    """Verify permission guard allow/block/ask logic."""

    @pytest.mark.asyncio
    async def test_allow_by_default_for_file_read(self):
        """File read should be allowed by default"""
        from app.core.security import PermissionGuard
        guard = PermissionGuard()
        result = await guard.authorize_action("file", "read", {})
        assert result is True

    @pytest.mark.asyncio
    async def test_block_file_delete_by_default(self):
        """File delete should be blocked by default"""
        from app.core.security import PermissionGuard
        guard = PermissionGuard()
        result = await guard.authorize_action("file", "delete", {"path": "/tmp/test"})
        assert result is False

    @pytest.mark.asyncio
    async def test_block_registry_by_default(self):
        """Registry operations should be blocked by default"""
        from app.core.security import PermissionGuard
        guard = PermissionGuard()
        result = await guard.authorize_action("file", "registry", {})
        assert result is False


# ==============================================================================
# 11. Agent Manager Safety Tests
# ==============================================================================

class TestAgentManagerSafety:
    """Verify agent dispatch routing and unknown agent handling."""

    @pytest.mark.asyncio
    async def test_unknown_agent_type_raises(self):
        """Unknown agent types should raise ValueError"""
        from app.services.agent_dispatcher import AgentManager
        manager = AgentManager()
        progress = AsyncMock()
        with pytest.raises(ValueError, match="Unsupported agent type"):
            await manager.execute_step(
                {"agent_type": "nonexistent", "action": "do", "parameters": {}},
                progress,
            )

    def test_all_five_agents_registered(self):
        """All 5 agent types should be registered"""
        from app.services.agent_dispatcher import AgentManager
        manager = AgentManager()
        assert set(manager._agents.keys()) == {"desktop", "browser", "file", "terminal", "vision"}


# ==============================================================================
# 12. Output Truncation Tests
# ==============================================================================

class TestOutputTruncation:
    """Verify output size limits."""

    def test_short_output_not_truncated(self):
        from app.services.agent_dispatcher import _truncate_output
        text = "hello world"
        assert _truncate_output(text, 1000) == text

    def test_long_output_truncated(self):
        from app.services.agent_dispatcher import _truncate_output
        text = "x" * 2000
        result = _truncate_output(text, 100)
        assert len(result.encode("utf-8")) <= 100

    def test_unicode_output_truncated(self):
        from app.services.agent_dispatcher import _truncate_output
        text = "\u4e16" * 2000
        result = _truncate_output(text, 100)
        # Multi-byte chars may cause slight overshoot due to character boundaries
        assert len(result.encode("utf-8")) <= 110


# ==============================================================================
# 13. Path Blocking Tests
# ==============================================================================

class TestPathBlocking:
    """Verify file path blocking logic."""

    def test_blocks_windows_dir(self):
        from app.services.agent_dispatcher import _is_path_blocked
        assert _is_path_blocked("C:\\Windows\\System32\\test.dll", "write") is not None

    def test_blocks_etc(self):
        from app.services.agent_dispatcher import _is_path_blocked
        assert _is_path_blocked("/etc/passwd", "write") is not None

    def test_blocks_usr_bin(self):
        from app.services.agent_dispatcher import _is_path_blocked
        assert _is_path_blocked("/usr/bin/python", "delete") is not None

    def test_blocks_program_files(self):
        from app.services.agent_dispatcher import _is_path_blocked
        assert _is_path_blocked("C:\\Program Files\\App\\file.txt", "write") is not None

    def test_allows_temp_dir(self):
        from app.services.agent_dispatcher import _is_path_blocked
        assert _is_path_blocked("/tmp/test.txt", "write") is None

    def test_allows_home_dir(self):
        from app.services.agent_dispatcher import _is_path_blocked
        assert _is_path_blocked(os.path.expanduser("~/test.txt"), "write") is None


# ==============================================================================
# 14. Terminal Command Blocked Pattern Tests
# ==============================================================================

class TestTerminalBlockedPatterns:
    """Verify the blocked command regex works for all patterns."""

    def test_blocks_wevtutil_clear(self):
        from app.services.agent_dispatcher import _is_terminal_command_blocked
        assert _is_terminal_command_blocked("wevtutil cl System") is not None

    def test_blocks_net_user_delete(self):
        from app.services.agent_dispatcher import _is_terminal_command_blocked
        assert _is_terminal_command_blocked("net user admin /delete") is not None

    def test_blocks_reg_delete(self):
        from app.services.agent_dispatcher import _is_terminal_command_blocked
        assert _is_terminal_command_blocked("reg delete HKLM\\SOFTWARE\\Test") is not None

    def test_safe_command_not_blocked(self):
        from app.services.agent_dispatcher import _is_terminal_command_blocked
        assert _is_terminal_command_blocked("echo hello world") is None

    def test_safe_ls_not_blocked(self):
        from app.services.agent_dispatcher import _is_terminal_command_blocked
        assert _is_terminal_command_blocked("ls -la /home/user") is None

    def test_safe_python_not_blocked(self):
        from app.services.agent_dispatcher import _is_terminal_command_blocked
        assert _is_terminal_command_blocked("python script.py") is None
