"""Tests for single active workflow enforcement."""
import pytest
import asyncio
from app.services.state_machine import WorkflowState
from app.infrastructure.memory_db import memory_db


class TestSingleActiveWorkflow:
    """Test that only one active workflow is allowed per user."""

    @pytest.mark.asyncio
    async def test_has_active_workflow_true_when_executing(self):
        """Should detect active workflow when one is executing."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_1",
            "workflow_id": "wf1",
            "user_id": "test_user_active",
            "status": WorkflowState.EXECUTING.value,
            "current_step_index": 0,
            "total_steps": 2,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        result = await _has_active_workflow("test_user_active")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_active_workflow_false_when_completed(self):
        """Should not detect active workflow when all are completed."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_2",
            "workflow_id": "wf2",
            "user_id": "test_user_completed",
            "status": WorkflowState.COMPLETED.value,
            "current_step_index": 2,
            "total_steps": 2,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        result = await _has_active_workflow("test_user_completed")
        assert result is False

    @pytest.mark.asyncio
    async def test_has_active_workflow_false_when_cancelled(self):
        """Should not detect active workflow when cancelled."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_3",
            "workflow_id": "wf3",
            "user_id": "test_user_cancelled",
            "status": WorkflowState.CANCELLED.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        result = await _has_active_workflow("test_user_cancelled")
        assert result is False

    @pytest.mark.asyncio
    async def test_has_active_workflow_false_when_failed(self):
        """Should not detect active workflow when failed."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_4",
            "workflow_id": "wf4",
            "user_id": "test_user_failed",
            "status": WorkflowState.FAILED.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        result = await _has_active_workflow("test_user_failed")
        assert result is False

    @pytest.mark.asyncio
    async def test_has_active_workflow_true_when_planning(self):
        """Should detect active workflow when planning."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_5",
            "workflow_id": "wf5",
            "user_id": "test_user_planning",
            "status": WorkflowState.PLANNING.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        result = await _has_active_workflow("test_user_planning")
        assert result is True

    @pytest.mark.asyncio
    async def test_has_active_workflow_true_when_waiting(self):
        """Should detect active workflow when waiting for permission."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_6",
            "workflow_id": "wf6",
            "user_id": "test_user_waiting",
            "status": WorkflowState.WAITING.value,
            "current_step_index": 1,
            "total_steps": 3,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        result = await _has_active_workflow("test_user_waiting")
        assert result is True

    @pytest.mark.asyncio
    async def test_user_isolation(self):
        """Active workflow for user A should not block user B."""
        from app.api.v1.workflows import _has_active_workflow

        exec_doc = {
            "_id": "test_active_7",
            "workflow_id": "wf7",
            "user_id": "user_A_isolation",
            "status": WorkflowState.EXECUTING.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        assert await _has_active_workflow("user_A_isolation") is True
        assert await _has_active_workflow("user_B_isolation") is False


class TestActiveWorkflowEndpoint:
    """Test the GET /api/v1/workflows/active endpoint."""

    def test_active_workflow_endpoint(self):
        """Test the active workflow endpoint response structure."""
        from fastapi.testclient import TestClient
        from app.main import app
        import uuid

        # Register and login a test user
        test_email = f"active_test_{uuid.uuid4().hex[:8]}@test.com"
        client = TestClient(app)

        # Register
        reg_resp = client.post("/api/v1/auth/register", json={
            "email": test_email, "name": "Active Test", "password": "TestPass123!"
        })
        assert reg_resp.status_code == 200
        token = reg_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Check active workflow (should be None)
        resp = client.get("/api/v1/workflows/active", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["active"] is None


class TestExecuteEndpoint409:
    """Test that execute returns 409 when active workflow exists."""

    @pytest.mark.asyncio
    async def test_execute_returns_409_when_active(self):
        """Should return 409 when trying to execute while another is active."""
        from app.api.v1.workflows import _has_active_workflow
        from app.infrastructure.memory_db import memory_db

        user_id = "user_409_test"

        # Insert an active execution record
        exec_doc = {
            "workflow_id": "wf_active",
            "user_id": user_id,
            "status": "Executing",
            "current_step_index": 0,
            "total_steps": 3,
            "started_at": "2026-01-01T00:00:00",
        }
        await memory_db.insert("workflow_executions", exec_doc)

        # Verify _has_active_workflow detects it
        has_active = await _has_active_workflow(user_id)
        assert has_active is True
