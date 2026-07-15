"""Tests for the abort endpoint improvements (Issue 2: cancellation)."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app
from app.api.deps import get_current_user
from app.core.database import db_manager


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


def _mock_user():
    user = MagicMock()
    user.id = ObjectId()
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "user"
    return user


@pytest.fixture(autouse=True)
def override_auth():
    saved = dict(app.dependency_overrides)
    mock_u = _mock_user()
    app.dependency_overrides[get_current_user] = lambda: mock_u
    prev_use_memory = db_manager.use_memory
    db_manager.use_memory = True
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)
    db_manager.use_memory = prev_use_memory


class TestAbortEndpoint:
    def test_abort_invalid_id_returns_400(self, client):
        resp = client.post("/api/v1/executions/invalid-id/abort")
        assert resp.status_code == 400

    def test_abort_nonexistent_returns_404(self, client):
        fake_id = str(ObjectId())
        resp = client.post(f"/api/v1/executions/{fake_id}/abort")
        assert resp.status_code == 404

    def test_abort_requires_auth(self, client):
        saved = dict(app.dependency_overrides)
        app.dependency_overrides.clear()
        try:
            fake_id = str(ObjectId())
            resp = client.post(f"/api/v1/executions/{fake_id}/abort")
            assert resp.status_code in (401, 403)
        finally:
            app.dependency_overrides.update(saved)


class TestWorkflowStateTransitions:
    def test_cancelled_is_terminal(self):
        from app.services.state_machine import VALID_TRANSITIONS, WorkflowState
        assert VALID_TRANSITIONS[WorkflowState.CANCELLED] == []

    def test_executing_can_transition_to_cancelled(self):
        from app.services.state_machine import VALID_TRANSITIONS, WorkflowState
        assert WorkflowState.CANCELLED in VALID_TRANSITIONS[WorkflowState.EXECUTING]

    def test_planning_can_transition_to_cancelled(self):
        from app.services.state_machine import VALID_TRANSITIONS, WorkflowState
        assert WorkflowState.CANCELLED in VALID_TRANSITIONS[WorkflowState.PLANNING]

    def test_idle_can_transition_to_cancelled(self):
        from app.services.state_machine import VALID_TRANSITIONS, WorkflowState
        assert WorkflowState.CANCELLED in VALID_TRANSITIONS[WorkflowState.IDLE]


class TestProcessManagerIntegration:
    def test_cancel_process_returns_false_when_no_process(self):
        from app.services.process_manager import cancel_process
        result = cancel_process("nonexistent-execution-id")
        assert result is False

    def test_cancel_process_returns_true_when_process_tracked(self):
        from app.services.process_manager import cancel_process, register_process, _running_processes
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        register_process("test-exec", mock_proc)

        with patch("app.services.process_manager.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch("app.services.process_manager.os") as mock_os:
                mock_os.getpgid.return_value = 100
                mock_os.killpg.return_value = None
                result = cancel_process("test-exec")

        assert result is True
        assert "test-exec" not in _running_processes


class TestWorkerCancellationCheck:
    def test_cancelled_status_value(self):
        from app.services.state_machine import WorkflowState
        assert WorkflowState.CANCELLED.value == "Cancelled"
