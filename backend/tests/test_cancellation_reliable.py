"""Tests for reliable cancellation of active workflows."""
import pytest
import asyncio
from bson import ObjectId
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.state_machine import WorkflowStateMachine, WorkflowState
from app.services.process_manager import cancel_process, register_process, _running_processes
from app.infrastructure.memory_db import memory_db


class TestCancellation:
    """Test cancellation mechanics."""

    @pytest.mark.asyncio
    async def test_cancel_transitions_to_cancelled(self):
        """Cancel should transition execution to CANCELLED state."""
        exec_doc = {
            "workflow_id": "wf1",
            "user_id": "user1",
            "status": WorkflowState.EXECUTING.value,
            "current_step_index": 0,
            "total_steps": 3,
            "started_at": "2026-01-01T00:00:00",
        }
        oid = await memory_db.insert("workflow_executions", exec_doc)
        exec_id = str(oid)

        result = await WorkflowStateMachine.transition_to(exec_id, WorkflowState.CANCELLED)
        assert result is True

        status = await WorkflowStateMachine.get_status(exec_id)
        assert status == WorkflowState.CANCELLED.value

    @pytest.mark.asyncio
    async def test_cancel_during_planning(self):
        """Can cancel from Planning state."""
        exec_doc = {
            "workflow_id": "wf2",
            "user_id": "user1",
            "status": WorkflowState.PLANNING.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        oid = await memory_db.insert("workflow_executions", exec_doc)
        result = await WorkflowStateMachine.transition_to(str(oid), WorkflowState.CANCELLED)
        assert result is True

    @pytest.mark.asyncio
    async def test_cancel_during_waiting(self):
        """Can cancel from Waiting state."""
        exec_doc = {
            "workflow_id": "wf3",
            "user_id": "user1",
            "status": WorkflowState.WAITING.value,
            "current_step_index": 1,
            "total_steps": 3,
            "started_at": "2026-01-01T00:00:00",
        }
        oid = await memory_db.insert("workflow_executions", exec_doc)
        result = await WorkflowStateMachine.transition_to(str(oid), WorkflowState.CANCELLED)
        assert result is True

    @pytest.mark.asyncio
    async def test_cannot_complete_after_cancel(self):
        """Cannot transition to COMPLETED after CANCELLED."""
        exec_doc = {
            "workflow_id": "wf4",
            "user_id": "user1",
            "status": WorkflowState.CANCELLED.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        oid = await memory_db.insert("workflow_executions", exec_doc)
        result = await WorkflowStateMachine.transition_to(str(oid), WorkflowState.COMPLETED)
        assert result is False

    @pytest.mark.asyncio
    async def test_cannot_retry_after_cancel(self):
        """Cannot transition to RETRY after CANCELLED."""
        exec_doc = {
            "workflow_id": "wf5",
            "user_id": "user1",
            "status": WorkflowState.CANCELLED.value,
            "current_step_index": 0,
            "total_steps": 1,
            "started_at": "2026-01-01T00:00:00",
        }
        oid = await memory_db.insert("workflow_executions", exec_doc)
        result = await WorkflowStateMachine.transition_to(str(oid), WorkflowState.RETRY)
        assert result is False


class TestProcessManagerCancellation:
    """Test process manager cancellation."""

    def test_cancel_nonexistent_returns_false(self):
        """Cancel with no tracked process returns False."""
        result = cancel_process("nonexistent_exec_id")
        assert result is False

    def test_cancel_removes_from_registry(self):
        """Cancel removes the process from the registry."""
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        _running_processes["test_cancel_reg"] = mock_proc
        cancel_process("test_cancel_reg")
        assert "test_cancel_reg" not in _running_processes

    def test_unrelated_processes_not_killed(self):
        """Cancelling one execution does not affect others."""
        mock_proc1 = MagicMock()
        mock_proc1.pid = 11111
        mock_proc2 = MagicMock()
        mock_proc2.pid = 22222

        _running_processes["exec_A"] = mock_proc1
        _running_processes["exec_B"] = mock_proc2

        cancel_process("exec_A")

        assert "exec_A" not in _running_processes
        assert "exec_B" in _running_processes

        _running_processes.pop("exec_B", None)


class TestWorkflowEngineCancellation:
    """Test that workflow engine prevents recovery after cancellation."""

    @pytest.mark.asyncio
    async def test_abort_execution_sets_cancelled(self):
        """abort_execution should set status to CANCELLED."""
        from app.services.workflow_engine import workflow_engine

        exec_doc = {
            "workflow_id": "wf_abort_1",
            "user_id": "user1",
            "status": WorkflowState.EXECUTING.value,
            "current_step_index": 0,
            "total_steps": 2,
            "started_at": "2026-01-01T00:00:00",
        }
        oid = await memory_db.insert("workflow_executions", exec_doc)

        await workflow_engine.abort_execution(str(oid))

        status = await WorkflowStateMachine.get_status(str(oid))
        # C3 fix: abort now sets STOPPING (worker transitions to CANCELLED)
        assert status == WorkflowState.STOPPING.value
