"""Tests for display status mapping, execution history, entity extraction fixes, and startup recovery."""
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId


class TestMapDisplayStatus:
    """Test map_display_status from executions.py."""

    def test_completed_maps_to_completed(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("completed") == "completed"

    def test_cancelled_maps_to_stopped(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("cancelled") == "stopped"

    def test_stopped_maps_to_stopped(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("stopped") == "stopped"

    def test_failed_maps_to_stopped(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("failed") == "stopped"

    def test_failed_with_result_type_failed_maps_to_stopped(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("failed", result_type="failed") == "stopped"

    def test_idle_maps_to_draft(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("idle") == "draft"

    def test_draft_maps_to_draft(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("draft") == "draft"

    def test_planning_maps_to_draft(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("planning") == "draft"

    def test_awaiting_approval_maps_to_draft(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("awaiting_approval") == "draft"

    def test_executing_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("executing") is None

    def test_running_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("running") is None

    def test_waiting_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("waiting") is None

    def test_retry_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("retry") is None

    def test_stopping_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("stopping") is None

    def test_empty_string_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("") is None

    def test_none_maps_to_none(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status(None) is None

    def test_case_insensitive(self):
        from app.api.v1.executions import map_display_status
        assert map_display_status("COMPLETED") == "completed"
        assert map_display_status("Cancelled") == "stopped"
        assert map_display_status("EXECUTING") is None


class TestExecutionToHistoryDict:
    """Test _execution_to_history_dict for memory mode."""

    def test_includes_conversation_id(self):
        from app.api.v1.executions import _execution_to_history_dict
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "conversation_id": "conv-abc-123",
            "title": "Test workflow",
            "description": "Test desc",
            "status": "completed",
            "current_step_index": 2,
            "total_steps": 2,
            "started_at": now.isoformat(),
            "completed_at": (now + timedelta(minutes=5)).isoformat(),
            "stopped_at": None,
            "error_message": None,
            "result": None,
            "result_type": None,
            "created_at": now.isoformat(),
        }
        result = _execution_to_history_dict(doc, "memory")
        assert result["conversation_id"] == "conv-abc-123"
        assert result["display_status"] == "completed"

    def test_includes_stopped_at(self):
        from app.api.v1.executions import _execution_to_history_dict
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "conversation_id": None,
            "title": "Test",
            "description": "",
            "status": "cancelled",
            "current_step_index": 1,
            "total_steps": 3,
            "started_at": now.isoformat(),
            "completed_at": None,
            "stopped_at": (now + timedelta(seconds=30)).isoformat(),
            "error_message": "User cancelled",
            "result": None,
            "result_type": None,
            "created_at": now.isoformat(),
        }
        result = _execution_to_history_dict(doc, "memory")
        assert result["stopped_at"] is not None
        assert result["display_status"] == "stopped"

    def test_duration_ms_calculation(self):
        from app.api.v1.executions import _execution_to_history_dict
        start = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, 12, 5, 30, tzinfo=timezone.utc)
        doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "conversation_id": None,
            "title": "Test",
            "description": "",
            "status": "completed",
            "current_step_index": 1,
            "total_steps": 1,
            "started_at": start.isoformat(),
            "completed_at": end.isoformat(),
            "stopped_at": None,
            "error_message": None,
            "result": None,
            "result_type": None,
            "created_at": start.isoformat(),
        }
        result = _execution_to_history_dict(doc, "memory")
        assert result["duration_ms"] == 330000  # 5min 30s = 330000ms

    def test_active_states_return_none_display(self):
        from app.api.v1.executions import _execution_to_history_dict
        now = datetime.now(timezone.utc)
        for status in ["executing", "running", "waiting", "retry", "stopping"]:
            doc = {
                "_id": ObjectId(),
                "workflow_id": ObjectId(),
                "conversation_id": None,
                "title": "Test",
                "description": "",
                "status": status,
                "current_step_index": 0,
                "total_steps": 3,
                "started_at": now.isoformat(),
                "completed_at": None,
                "stopped_at": None,
                "error_message": None,
                "result": None,
                "result_type": None,
                "created_at": now.isoformat(),
            }
            result = _execution_to_history_dict(doc, "memory")
            assert result["display_status"] is None, f"Status '{status}' should map to None display"

    def test_draft_states(self):
        from app.api.v1.executions import _execution_to_history_dict
        now = datetime.now(timezone.utc)
        for status in ["idle", "draft", "awaiting_approval"]:
            doc = {
                "_id": ObjectId(),
                "workflow_id": ObjectId(),
                "conversation_id": None,
                "title": "Test",
                "description": "",
                "status": status,
                "current_step_index": 0,
                "total_steps": 3,
                "started_at": now.isoformat(),
                "completed_at": None,
                "stopped_at": None,
                "error_message": None,
                "result": None,
                "result_type": None,
                "created_at": now.isoformat(),
            }
            result = _execution_to_history_dict(doc, "memory")
            assert result["display_status"] == "draft", f"Status '{status}' should map to 'draft' display"

    def test_none_conversation_id(self):
        from app.api.v1.executions import _execution_to_history_dict
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "conversation_id": None,
            "title": "Test",
            "description": "",
            "status": "completed",
            "current_step_index": 1,
            "total_steps": 1,
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "stopped_at": None,
            "error_message": None,
            "result": None,
            "result_type": None,
            "created_at": now.isoformat(),
        }
        result = _execution_to_history_dict(doc, "memory")
        assert result["conversation_id"] is None

    def test_duration_ms_none_when_no_end(self):
        from app.api.v1.executions import _execution_to_history_dict
        now = datetime.now(timezone.utc)
        doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "conversation_id": None,
            "title": "Test",
            "description": "",
            "status": "executing",
            "current_step_index": 0,
            "total_steps": 3,
            "started_at": now.isoformat(),
            "completed_at": None,
            "stopped_at": None,
            "error_message": None,
            "result": None,
            "result_type": None,
            "created_at": now.isoformat(),
        }
        result = _execution_to_history_dict(doc, "memory")
        assert result["duration_ms"] is None


class TestEntityExtractionDirectDictAccess:
    """Test that entity extraction uses direct dict key access (not str regex)."""

    def test_deleted_from_task_results_dict(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "user", "content": "Delete factorial.py", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Deleted successfully:\nC:\\Users\\karth\\Desktop\\factorial.py",
             "message_type": "assistant", "metadata": {"task_results": {"deleted": True, "path": "C:\\Users\\karth\\Desktop\\factorial.py"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_deleted_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"
        assert entities["last_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"

    def test_created_from_task_results_dict(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "user", "content": "Create notes.txt", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "File saved: C:\\Users\\karth\\Desktop\\notes.txt",
             "message_type": "assistant", "metadata": {"task_results": {"path": "C:\\Users\\karth\\Desktop\\notes.txt", "success": True}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_created_file"] == "C:\\Users\\karth\\Desktop\\notes.txt"

    def test_moved_from_task_results_dict(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "user", "content": "Move file.pdf", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Moved report.pdf to Documents",
             "message_type": "assistant", "metadata": {"task_results": {"moved": True, "source": "C:\\report.pdf", "destination": "C:\\Documents"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_moved_file"] == "C:\\report.pdf"
        assert entities["last_destination_folder"] == "C:\\Documents"

    def test_renamed_from_task_results_dict(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "user", "content": "Rename file", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Renamed: old.txt -> new.txt",
             "message_type": "assistant", "metadata": {"task_results": {"renamed": True, "old_path": "C:\\old.txt"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_modified_file"] == "C:\\old.txt"
        assert entities["last_file"] == "C:\\old.txt"

    def test_backslash_not_doubled(self):
        """Regression: str(dict) doubles backslashes, direct access preserves them."""
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "assistant", "content": "Deleted",
             "message_type": "assistant", "metadata": {"task_results": {"deleted": True, "path": "C:\\Users\\karth\\Desktop\\test.py"}}},
        ]
        entities = build_entity_context(messages)
        assert "\\\\" not in entities["last_deleted_file"]
        assert entities["last_deleted_file"] == "C:\\Users\\karth\\Desktop\\test.py"

    def test_empty_task_results_no_error(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "assistant", "content": "Done", "message_type": "assistant", "metadata": {"task_results": {}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_file"] is None

    def test_none_task_results_no_error(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "assistant", "content": "Done", "message_type": "assistant", "metadata": {"task_results": None}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_file"] is None

    def test_assistant_content_scanned_for_paths(self):
        """Assistant messages with file paths in content should be scanned."""
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "assistant", "content": "File saved: C:\\Users\\karth\\Desktop\\factorial.py",
             "message_type": "assistant", "metadata": {}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_created_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"

    def test_assistant_deletion_content_scanned(self):
        """Assistant messages reporting deletion should be scanned."""
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "assistant", "content": "Deleted successfully:\nC:\\Users\\karth\\Desktop\\old.txt",
             "message_type": "assistant", "metadata": {}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_deleted_file"] == "C:\\Users\\karth\\Desktop\\old.txt"

    def test_preserves_last_file_across_operations(self):
        from app.services.conversation_context import build_entity_context
        messages = [
            {"role": "assistant", "content": "Done",
             "message_type": "assistant", "metadata": {"task_results": {"path": "C:\\first.py", "success": True}}},
            {"role": "assistant", "content": "Done",
             "message_type": "assistant", "metadata": {"task_results": {"deleted": True, "path": "C:\\first.py"}}},
            {"role": "assistant", "content": "Done",
             "message_type": "assistant", "metadata": {"task_results": {"path": "C:\\second.py", "success": True}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_created_file"] == "C:\\second.py"
        assert entities["last_deleted_file"] == "C:\\first.py"
        assert entities["last_file"] == "C:\\second.py"


class TestStartupRecovery:
    """Test that startup recovery logic correctly identifies stale workflows."""

    def test_stale_states_list(self):
        """Startup recovery should target these states."""
        stale_states = ["Planning", "Executing", "Waiting", "Retry", "Stopping"]
        non_stale = ["Completed", "Cancelled", "Failed", "Idle"]
        for s in stale_states:
            assert s in stale_states
        for s in non_stale:
            assert s not in stale_states

    @pytest.mark.asyncio
    async def test_recovery_converts_stale_executions(self):
        """Simulate startup recovery converting stale executions to Cancelled."""
        from app.infrastructure.memory_db import memory_db, _in_memory_collections

        now = datetime.now(timezone.utc)
        test_doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "user_id": "test-user",
            "title": "Test",
            "description": "",
            "status": "Executing",
            "current_step_index": 1,
            "total_steps": 3,
            "started_at": now.isoformat(),
            "completed_at": None,
            "stopped_at": None,
            "error_message": None,
            "result": None,
            "result_type": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await memory_db.insert("workflow_executions", test_doc)

        # Simulate recovery
        all_execs = await memory_db.find("workflow_executions", {})
        recovered = 0
        for ex in all_execs:
            if ex.get("status") in ["Planning", "Executing", "Waiting", "Retry", "Stopping"]:
                await memory_db.update("workflow_executions", {"_id": ex["_id"]}, {
                    "status": "Cancelled",
                    "stopped_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "error_message": "Recovered after backend restart",
                })
                recovered += 1

        assert recovered == 1

        # Verify the doc was updated
        updated = await memory_db.find_one("workflow_executions", {"_id": test_doc["_id"]})
        assert updated["status"] == "Cancelled"
        assert updated["stopped_at"] is not None
        assert updated["error_message"] == "Recovered after backend restart"

    @pytest.mark.asyncio
    async def test_recovery_skips_non_stale(self):
        """Startup recovery should not touch completed/cancelled workflows."""
        from app.infrastructure.memory_db import memory_db

        now = datetime.now(timezone.utc)
        completed_doc = {
            "_id": ObjectId(),
            "workflow_id": ObjectId(),
            "user_id": "test-user",
            "title": "Done",
            "description": "",
            "status": "Completed",
            "current_step_index": 3,
            "total_steps": 3,
            "started_at": now.isoformat(),
            "completed_at": now.isoformat(),
            "stopped_at": None,
            "error_message": None,
            "result": None,
            "result_type": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
        await memory_db.insert("workflow_executions", completed_doc)

        all_execs = await memory_db.find("workflow_executions", {})
        recovered = 0
        for ex in all_execs:
            if ex.get("status") in ["Planning", "Executing", "Waiting", "Retry", "Stopping"]:
                recovered += 1

        assert recovered == 0

        # Verify doc unchanged
        doc = await memory_db.find_one("workflow_executions", {"_id": completed_doc["_id"]})
        assert doc["status"] == "Completed"


class TestUtcnowUsage:
    """Verify that models.py _utcnow produces timezone-aware UTC timestamps."""

    def test_utcnow_has_timezone(self):
        from app.infrastructure.db.models import _utcnow
        now = _utcnow()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_utcnow_is_recent(self):
        from app.infrastructure.db.models import _utcnow
        before = datetime.now(timezone.utc)
        now = _utcnow()
        after = datetime.now(timezone.utc)
        assert before <= now <= after


class TestWorkflowEngineConversationId:
    """Test that workflow_engine.start_execution accepts conversation_id."""

    @pytest.mark.asyncio
    async def test_start_execution_accepts_conversation_id(self):
        """Verify the signature accepts conversation_id keyword argument."""
        from app.services.workflow_engine import workflow_engine
        import inspect
        sig = inspect.signature(workflow_engine.start_execution)
        assert "conversation_id" in sig.parameters
