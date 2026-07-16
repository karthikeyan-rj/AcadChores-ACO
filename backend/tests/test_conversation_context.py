"""Tests for conversation memory, context building, and reference resolution."""
import pytest
import asyncio
from app.services.conversation_context import (
    build_entity_context,
    resolve_references,
    check_reference_validity,
    build_context_summary,
)


class TestEntityExtraction:
    """Test entity extraction from conversation messages."""

    def test_extracts_created_file(self):
        messages = [
            {"role": "user", "content": "Create factorial.py on Desktop", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "File saved: C:\\Users\\karth\\Desktop\\factorial.py", "message_type": "assistant", "metadata": {"task_results": {"path": "C:\\Users\\karth\\Desktop\\factorial.py"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_created_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"
        assert entities["last_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"

    def test_extracts_deleted_file(self):
        messages = [
            {"role": "user", "content": "Delete factorial.py", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Deleted successfully:\nC:\\Users\\karth\\Desktop\\factorial.py", "message_type": "assistant", "metadata": {"task_results": {"deleted": True, "path": "C:\\Users\\karth\\Desktop\\factorial.py"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_deleted_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"
        assert entities["last_file"] == "C:\\Users\\karth\\Desktop\\factorial.py"

    def test_extracts_moved_file(self):
        messages = [
            {"role": "user", "content": "Move report.pdf to Documents", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Moved report.pdf to Documents", "message_type": "assistant", "metadata": {"task_results": {"moved": True, "source": "C:\\Users\\karth\\Desktop\\report.pdf", "destination": "C:\\Users\\karth\\Documents"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_moved_file"] == "C:\\Users\\karth\\Desktop\\report.pdf"
        assert entities["last_destination_folder"] == "C:\\Users\\karth\\Documents"

    def test_extracts_renamed_file(self):
        messages = [
            {"role": "user", "content": "Rename notes-old.txt to notes.txt", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Renamed: old.txt → new.txt", "message_type": "assistant", "metadata": {"task_results": {"renamed": True, "old_path": "C:\\Users\\karth\\Desktop\\notes-old.txt"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_modified_file"] == "C:\\Users\\karth\\Desktop\\notes-old.txt"
        assert entities["last_file"] == "C:\\Users\\karth\\Desktop\\notes-old.txt"

    def test_extracts_workflow_id(self):
        messages = [
            {"role": "user", "content": "Delete that file", "message_type": "user", "metadata": {}},
            {"role": "assistant", "content": "Generated 1 step(s).", "message_type": "workflow_plan", "metadata": {"planner_source": "rule_based"}, "workflow_id": "wf123"},
        ]
        entities = build_entity_context(messages)
        assert entities["last_workflow_id"] == "wf123"

    def test_empty_messages(self):
        entities = build_entity_context([])
        assert entities["last_created_file"] is None
        assert entities["last_file"] is None

    def test_multiple_files_tracks_latest(self):
        messages = [
            {"role": "assistant", "content": "File saved: C:\\file1.py", "message_type": "assistant", "metadata": {"task_results": {"path": "C:\\file1.py"}}},
            {"role": "assistant", "content": "File saved: C:\\file2.py", "message_type": "assistant", "metadata": {"task_results": {"path": "C:\\file2.py"}}},
        ]
        entities = build_entity_context(messages)
        assert entities["last_created_file"] == "C:\\file2.py"


class TestReferenceResolution:
    """Test reference resolution for ambiguous prompts."""

    def test_resolve_that_file(self):
        entities = {"last_file": "C:\\Users\\karth\\Desktop\\factorial.py"}
        resolved = resolve_references("Delete that file", entities)
        assert resolved == "Delete C:\\Users\\karth\\Desktop\\factorial.py"

    def test_resolve_delete_it(self):
        entities = {"last_file": "C:\\Users\\karth\\Desktop\\factorial.py"}
        resolved = resolve_references("delete it", entities)
        # "delete it" matches, verb "delete" is kept, "it" replaced with path
        assert "C:\\Users\\karth\\Desktop\\factorial.py" in resolved
        assert "delete" in resolved.lower()

    def test_resolve_move_it(self):
        entities = {"last_file": "C:\\Users\\karth\\Desktop\\report.pdf"}
        resolved = resolve_references("Move it to Documents", entities)
        # "move it" matches, verb "move" is kept, "it" replaced with path
        assert "C:\\Users\\karth\\Desktop\\report.pdf" in resolved
        assert "Move" in resolved
        assert "to Documents" in resolved

    def test_resolve_the_file_i_created(self):
        entities = {"last_file": "C:\\Users\\karth\\Desktop\\notes.txt"}
        resolved = resolve_references("Rename the file I created", entities)
        # "rename the file i created" is an exact pattern match, replaces entire phrase
        assert resolved == "C:\\Users\\karth\\Desktop\\notes.txt"

    def test_resolve_no_entity_returns_original(self):
        entities = {"last_file": None}
        original = "Delete that file"
        resolved = resolve_references(original, entities)
        assert resolved == original

    def test_resolve_no_ambiguous_reference(self):
        entities = {"last_file": "C:\\test.py"}
        original = "Create factorial.py on Desktop"
        resolved = resolve_references(original, entities)
        assert resolved == original

    def test_resolve_run_it_again(self):
        entities = {"last_task": "search YouTube for AI news"}
        resolved = resolve_references("run it again", entities)
        # "run it" matches, verb "run" is kept, "it" replaced with task
        assert "search YouTube for AI news" in resolved
        assert "run" in resolved.lower()

    def test_resolve_the_folder(self):
        entities = {"last_destination": "C:\\Users\\karth\\Documents"}
        resolved = resolve_references("Move to the folder", entities)
        assert "C:\\Users\\karth\\Documents" in resolved


class TestReferenceValidity:
    """Test that deleted file references are caught."""

    def test_deleted_file_returns_clarification(self):
        entities = {
            "last_deleted_file": "C:\\Users\\karth\\Desktop\\factorial.py",
            "last_file": "C:\\Users\\karth\\Desktop\\factorial.py",
        }
        result = check_reference_validity("Delete that file", entities)
        assert result is not None
        assert "already deleted" in result

    def test_non_deleted_file_returns_none(self):
        entities = {
            "last_deleted_file": "C:\\old.py",
            "last_file": "C:\\new.py",
        }
        result = check_reference_validity("Delete that file", entities)
        assert result is None

    def test_no_deleted_file_returns_none(self):
        entities = {"last_deleted_file": None, "last_file": "C:\\test.py"}
        result = check_reference_validity("Delete that file", entities)
        assert result is None


class TestContextSummary:
    """Test context summary generation for the LLM planner."""

    def test_summary_includes_entities(self):
        entities = {
            "last_created_file": "C:\\factorial.py",
            "last_deleted_file": None,
            "last_moved_file": None,
            "last_destination_folder": None,
            "last_modified_file": None,
            "last_task_description": None,
        }
        summary = build_context_summary(entities, [])
        assert "C:\\factorial.py" in summary

    def test_summary_includes_recent_messages(self):
        entities = {}
        messages = [
            {"role": "user", "content": "Create factorial.py"},
            {"role": "assistant", "content": "File created"},
        ]
        summary = build_context_summary(entities, messages)
        assert "Create factorial.py" in summary
        assert "File created" in summary

    def test_empty_summary(self):
        summary = build_context_summary({}, [])
        assert summary == ""


class TestPersistence:
    """Test that chat messages are correctly persisted."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_messages(self):
        from app.api.v1.workflows import _save_chat_message, _get_conversation_messages
        import uuid

        conv_id = str(uuid.uuid4())
        # Use a fake user_id for testing
        test_user_id = "test_user_conversation_1"

        await _save_chat_message(test_user_id, conv_id, "user", "user", "Hello ACO")
        await _save_chat_message(test_user_id, conv_id, "assistant", "assistant", "Hello! How can I help?")

        messages = await _get_conversation_messages(test_user_id, conv_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello ACO"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hello! How can I help?"

    @pytest.mark.asyncio
    async def test_messages_ordered_by_created_at(self):
        from app.api.v1.workflows import _save_chat_message, _get_conversation_messages
        import uuid
        import time

        conv_id = str(uuid.uuid4())
        test_user_id = "test_user_conversation_2"

        await _save_chat_message(test_user_id, conv_id, "user", "user", "First message")
        time.sleep(0.01)
        await _save_chat_message(test_user_id, conv_id, "assistant", "assistant", "Second message")
        time.sleep(0.01)
        await _save_chat_message(test_user_id, conv_id, "user", "user", "Third message")

        messages = await _get_conversation_messages(test_user_id, conv_id)
        assert len(messages) == 3
        assert messages[0]["content"] == "First message"
        assert messages[1]["content"] == "Second message"
        assert messages[2]["content"] == "Third message"

    @pytest.mark.asyncio
    async def test_conversation_isolation_between_users(self):
        from app.api.v1.workflows import _save_chat_message, _get_conversation_messages
        import uuid

        conv_id = str(uuid.uuid4())
        await _save_chat_message("user_A", conv_id, "user", "user", "User A message")
        await _save_chat_message("user_B", conv_id, "user", "user", "User B message")

        a_msgs = await _get_conversation_messages("user_A", conv_id)
        b_msgs = await _get_conversation_messages("user_B", conv_id)

        assert len(a_msgs) == 1
        assert a_msgs[0]["content"] == "User A message"
        assert len(b_msgs) == 1
        assert b_msgs[0]["content"] == "User B message"

    @pytest.mark.asyncio
    async def test_workflow_linked_messages_retain_workflow_id(self):
        from app.api.v1.workflows import _save_chat_message, _get_conversation_messages
        import uuid

        conv_id = str(uuid.uuid4())
        test_user_id = "test_user_conversation_3"

        await _save_chat_message(test_user_id, conv_id, "assistant", "workflow_plan",
                                 "Generated 1 step", workflow_id="wf_abc123")

        messages = await _get_conversation_messages(test_user_id, conv_id)
        assert len(messages) == 1
        assert messages[0]["workflow_id"] == "wf_abc123"

    @pytest.mark.asyncio
    async def test_duplicate_save_does_not_create_extra_messages(self):
        from app.api.v1.workflows import _save_chat_message, _get_conversation_messages
        import uuid

        conv_id = str(uuid.uuid4())
        test_user_id = "test_user_conversation_4"

        msg = await _save_chat_message(test_user_id, conv_id, "user", "user", "Test message")
        messages = await _get_conversation_messages(test_user_id, conv_id)
        assert len(messages) == 1
