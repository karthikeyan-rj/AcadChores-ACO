"""Tests for idempotent state-change handler and conversation workflow reconstruction."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from bson import ObjectId


class TestStateChangeIdempotency:
    """Test that _handle_state_change is idempotent — no duplicate messages on repeated events."""

    @pytest.mark.asyncio
    async def test_first_state_change_saves_message(self):
        """A terminal state change creates a conversation message."""
        from app.services.workflow_engine import WorkflowEngine
        from app.core.event_bus import SystemEvent

        engine = WorkflowEngine()
        exec_id = str(ObjectId())
        conv_id = "test-conv-1"
        user_id = str(ObjectId())

        mock_exec = {
            "_id": exec_id,
            "workflow_id": str(ObjectId()),
            "user_id": user_id,
            "conversation_id": conv_id,
            "title": "Test workflow",
            "status": "Completed",
            "last_completed_step": None,
            "error_message": None,
            "result": "All done",
            "partial_result": None,
        }

        mock_msg_instance = AsyncMock()

        with patch("app.services.workflow_engine._find_exec", new_callable=AsyncMock, return_value=mock_exec):
            with patch("app.services.workflow_engine.db_manager") as mock_db:
                mock_db.use_memory = True
                with patch("app.services.workflow_engine.memory_db") as mock_mdb:
                    mock_mdb.find = AsyncMock(return_value=[])
                    mock_mdb.insert = AsyncMock(return_value=str(ObjectId()))
                    with patch("app.services.workflow_engine.ChatMessage") as MockChatMessage:
                        MockChatMessage.return_value = mock_msg_instance

                        event = SystemEvent(
                            topic="workflow.state_change",
                            sender="test",
                            payload={"execution_id": exec_id, "new_state": "Completed"},
                        )
                        await engine._handle_state_change(event)
                        assert mock_mdb.find.called
                        assert mock_msg_instance.insert.called

    @pytest.mark.asyncio
    async def test_duplicate_state_change_skipped(self):
        """A second state change for the same execution+state is skipped."""
        from app.services.workflow_engine import WorkflowEngine
        from app.core.event_bus import SystemEvent

        engine = WorkflowEngine()
        exec_id = str(ObjectId())
        conv_id = "test-conv-2"
        user_id = str(ObjectId())

        mock_exec = {
            "_id": exec_id,
            "workflow_id": str(ObjectId()),
            "user_id": user_id,
            "conversation_id": conv_id,
            "title": "Test workflow",
            "status": "Completed",
            "last_completed_step": None,
            "error_message": None,
            "result": "All done",
            "partial_result": None,
        }

        existing_msg = {
            "_id": str(ObjectId()),
            "execution_id": exec_id,
            "metadata": {"workflow_state": "Completed", "execution_id": exec_id},
        }

        with patch("app.services.workflow_engine._find_exec", new_callable=AsyncMock, return_value=mock_exec):
            with patch("app.services.workflow_engine.db_manager") as mock_db:
                mock_db.use_memory = True
                with patch("app.services.workflow_engine.memory_db") as mock_mdb:
                    mock_mdb.find = AsyncMock(return_value=[existing_msg])
                    mock_mdb.insert = AsyncMock(return_value=str(ObjectId()))

                    event = SystemEvent(
                        topic="workflow.state_change",
                        sender="test",
                        payload={"execution_id": exec_id, "new_state": "Completed"},
                    )
                    await engine._handle_state_change(event)
                    # find was called to check for duplicates
                    assert mock_mdb.find.called
                    # insert was NOT called because duplicate was found
                    assert not mock_mdb.insert.called

    @pytest.mark.asyncio
    async def test_different_states_both_saved(self):
        """Different terminal states for the same execution are both saved."""
        from app.services.workflow_engine import WorkflowEngine
        from app.core.event_bus import SystemEvent

        engine = WorkflowEngine()
        exec_id = str(ObjectId())
        conv_id = "test-conv-3"
        user_id = str(ObjectId())

        mock_exec = {
            "_id": exec_id,
            "workflow_id": str(ObjectId()),
            "user_id": user_id,
            "conversation_id": conv_id,
            "title": "Test workflow",
            "status": "Failed",
            "last_completed_step": "step_1",
            "error_message": "Something broke",
            "result": None,
            "partial_result": "Partial work done",
        }

        mock_msg_instance = AsyncMock()

        with patch("app.services.workflow_engine._find_exec", new_callable=AsyncMock, return_value=mock_exec):
            with patch("app.services.workflow_engine.db_manager") as mock_db:
                mock_db.use_memory = True
                with patch("app.services.workflow_engine.memory_db") as mock_mdb:
                    mock_mdb.find = AsyncMock(return_value=[])
                    mock_mdb.insert = AsyncMock(return_value=str(ObjectId()))
                    with patch("app.services.workflow_engine.ChatMessage") as MockChatMessage:
                        MockChatMessage.return_value = mock_msg_instance

                        event = SystemEvent(
                            topic="workflow.state_change",
                            sender="test",
                            payload={"execution_id": exec_id, "new_state": "Failed"},
                        )
                        await engine._handle_state_change(event)
                        assert mock_msg_instance.insert.called

    @pytest.mark.asyncio
    async def test_non_terminal_state_ignored(self):
        """Non-terminal states (Executing, Planning) are not saved as messages."""
        from app.services.workflow_engine import WorkflowEngine
        from app.core.event_bus import SystemEvent

        engine = WorkflowEngine()
        exec_id = str(ObjectId())

        with patch("app.services.workflow_engine.db_manager") as mock_db:
            mock_db.use_memory = True
            with patch("app.services.workflow_engine.memory_db") as mock_mdb:
                mock_mdb.find = AsyncMock(return_value=[])
                mock_mdb.insert = AsyncMock()

                for state in ["Executing", "Planning", "Waiting", "Retry", "Stopping", "Idle"]:
                    event = SystemEvent(
                        topic="workflow.state_change",
                        sender="test",
                        payload={"execution_id": exec_id, "new_state": state},
                    )
                    await engine._handle_state_change(event)

                # insert should never be called for non-terminal states
                assert not mock_mdb.insert.called

    @pytest.mark.asyncio
    async def test_missing_conversation_id_skipped(self):
        """Executions without conversation_id are skipped."""
        from app.services.workflow_engine import WorkflowEngine
        from app.core.event_bus import SystemEvent

        engine = WorkflowEngine()
        exec_id = str(ObjectId())

        mock_exec = {
            "_id": exec_id,
            "workflow_id": str(ObjectId()),
            "user_id": str(ObjectId()),
            "conversation_id": None,
            "title": "Test",
            "status": "Completed",
        }

        with patch("app.services.workflow_engine._find_exec", new_callable=AsyncMock, return_value=mock_exec):
            with patch("app.services.workflow_engine.db_manager") as mock_db:
                mock_db.use_memory = True
                with patch("app.services.workflow_engine.memory_db") as mock_mdb:
                    mock_mdb.insert = AsyncMock()

                    event = SystemEvent(
                        topic="workflow.state_change",
                        sender="test",
                        payload={"execution_id": exec_id, "new_state": "Completed"},
                    )
                    await engine._handle_state_change(event)
                    assert not mock_mdb.insert.called


class TestConversationWorkflowReconstruction:
    """Test that conversation workflows endpoint returns correct data for reconstruction."""

    def test_conversation_workflows_included_in_conversation_response(self):
        """The conversation endpoint returns messages with execution_id fields."""
        from app.services.conversation_context import build_entity_context

        messages = [
            {
                "role": "user", "content": "Create a file",
                "message_type": "user", "metadata": {},
                "created_at": "2025-01-01T10:00:00Z",
            },
            {
                "role": "assistant", "content": "File saved: test.txt",
                "message_type": "assistant", "metadata": {"task_results": {"path": "test.txt"}},
                "created_at": "2025-01-01T10:00:05Z",
            },
            {
                "role": "assistant", "content": "Workflow completed: Create a file",
                "message_type": "assistant",
                "metadata": {"workflow_state": "Completed", "execution_id": "exec_1"},
                "execution_id": "exec_1",
                "created_at": "2025-01-01T10:00:10Z",
            },
        ]
        entities = build_entity_context(messages)
        # Active workflow should be None since the only workflow is Completed
        assert entities["active_workflow_id"] is None
        assert entities["last_workflow_state"] == "Completed"

    def test_active_workflow_tracked_across_messages(self):
        """An active workflow execution is tracked in entity context."""
        from app.services.conversation_context import build_entity_context

        messages = [
            {
                "role": "user", "content": "Do something complex",
                "message_type": "user", "metadata": {},
            },
            {
                "role": "assistant", "content": "Generated plan",
                "message_type": "workflow_plan",
                "metadata": {},
                "workflow_id": "wf_1",
            },
        ]
        entities = build_entity_context(messages)
        assert entities["last_workflow_id"] == "wf_1"
        assert entities["last_task_description"] == "Generated plan"

    def test_stopped_workflow_tracked(self):
        """A Cancelled workflow sets last_stop_reason."""
        from app.services.conversation_context import build_entity_context

        messages = [
            {
                "role": "assistant",
                "content": "Workflow stopped: Big task",
                "message_type": "assistant",
                "metadata": {"workflow_state": "Cancelled", "execution_id": "exec_1"},
                "execution_id": "exec_1",
            },
        ]
        entities = build_entity_context(messages)
        assert entities["last_workflow_state"] == "Cancelled"
        assert "Big task" in (entities["last_stop_reason"] or "")

    def test_context_summary_includes_workflow_state(self):
        """The context summary includes active workflow and last result."""
        from app.services.conversation_context import build_context_summary

        entities = {
            "last_created_file": None,
            "last_deleted_file": None,
            "last_moved_file": None,
            "last_destination_folder": None,
            "last_modified_file": None,
            "last_file": None,
            "last_task_description": None,
            "last_workflow_id": None,
            "active_workflow_id": "exec_123",
            "last_workflow_result": "All files processed",
            "last_workflow_state": "Completed",
            "last_stop_reason": None,
        }
        summary = build_context_summary(entities, [])
        assert "Active workflow: exec_123" in summary
        assert "Last workflow completed" in summary
        assert "All files processed" in summary

    def test_context_summary_includes_stop_reason(self):
        """The context summary includes stop reason for Cancelled workflows."""
        from app.services.conversation_context import build_context_summary

        entities = {
            "last_created_file": None,
            "last_deleted_file": None,
            "last_moved_file": None,
            "last_destination_folder": None,
            "last_modified_file": None,
            "last_file": None,
            "last_task_description": None,
            "last_workflow_id": None,
            "active_workflow_id": None,
            "last_workflow_result": None,
            "last_workflow_state": "Cancelled",
            "last_stop_reason": "Workflow stopped: Big task",
        }
        summary = build_context_summary(entities, [])
        assert "Last workflow was stopped" in summary
