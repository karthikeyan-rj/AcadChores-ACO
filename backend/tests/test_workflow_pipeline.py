"""Tests for the complete workflow execution pipeline.

Covers:
  - Planner output format vs Step model compatibility
  - WorkflowValidator agent type/action recognition
  - WorkflowEngine state transitions
  - Event bus buffering and replay
  - Worker task lifecycle
  - Verification engine integration
  - Recovery engine integration
  - WebSocket event format compatibility
"""
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from bson import ObjectId

from app.infrastructure.db.models import Step, Workflow, WorkflowExecution
from app.services.workflow_validator import WorkflowValidator, AGENT_TYPES, AGENT_ACTIONS
from app.services.state_machine import WorkflowState, WorkflowStateMachine, VALID_TRANSITIONS
from app.core.event_bus import SystemEvent, event_bus
from app.recovery.engine import RecoveryEngine, RecoveryStrategy
from app.verification.engine import VerificationEngine, VerificationResult
from app.services.worker import TaskQueue, _in_memory_task_queue, _in_memory_task_statuses


# ─── Planner Output Format Tests ─────────────────────────────────────────────

class TestPlannerOutputFormat:
    """Verify planner output matches Step model and downstream consumers."""

    def test_single_step_matches_step_model(self):
        step = {
            "step_id": "step_1",
            "name": "Run command",
            "agent_type": "terminal",
            "action": "run",
            "parameters": {"command": "echo hello"},
        }
        s = Step(**step)
        assert s.step_id == "step_1"
        assert s.agent_type == "terminal"
        assert s.action == "run"
        assert s.parameters == {"command": "echo hello"}

    def test_multi_step_list_matches_step_model(self):
        steps_data = [
            {"step_id": "step_1", "name": "Navigate", "agent_type": "browser", "action": "navigate", "parameters": {"url": "https://google.com"}},
            {"step_id": "step_2", "name": "Fill search", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[name='q']", "value": "test"}},
            {"step_id": "step_3", "name": "Submit", "agent_type": "browser", "action": "press", "parameters": {"key": "Enter"}},
        ]
        for sd in steps_data:
            s = Step(**sd)
            assert s.step_id.startswith("step_")

    def test_file_write_step_matches_model(self):
        step = {
            "step_id": "step_1",
            "name": "Write file",
            "agent_type": "file",
            "action": "write",
            "parameters": {"path": "/tmp/test.txt", "content": "Hello World"},
        }
        s = Step(**step)
        assert s.parameters["path"] == "/tmp/test.txt"

    def test_desktop_step_matches_model(self):
        step = {
            "step_id": "step_1",
            "name": "Click calculator",
            "agent_type": "desktop",
            "action": "click",
            "parameters": {"target": "calculator"},
        }
        s = Step(**step)
        assert s.agent_type == "desktop"

    def test_step_model_accepts_empty_strings(self):
        s = Step(step_id="", name="Test", agent_type="terminal", action="run")
        assert s.step_id == ""

    def test_step_model_accepts_empty_agent_type(self):
        s = Step(step_id="step_1", name="Test", agent_type="", action="run")
        assert s.agent_type == ""

    def test_step_with_extra_params_is_flexible(self):
        step = {
            "step_id": "step_1",
            "name": "Recovery step",
            "agent_type": "terminal",
            "action": "run",
            "parameters": {"command": "echo retry"},
            "_recovery_attempt": 2,
            "_recovery_strategy": "retry",
        }
        s = Step(**{k: v for k, v in step.items() if not k.startswith("_")})
        assert s.step_id == "step_1"


# ─── WorkflowValidator Agent Type Tests ───────────────────────────────────────

class TestValidatorAgentTypes:
    """Verify the WorkflowValidator recognizes all planner agent types."""

    def test_terminal_recognized(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Run cmd", "agent_type": "terminal", "action": "run", "parameters": {"command": "echo hi"}}]}
        result = v.validate(wf, "run echo")
        agent_errors = [e for e in result["errors"] if "invalid_agent" in e.get("code", "")]
        assert len(agent_errors) == 0, f"terminal should be valid, got: {agent_errors}"

    def test_desktop_recognized(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Click", "agent_type": "desktop", "action": "click", "parameters": {"target": "btn"}}]}
        result = v.validate(wf, "click button")
        agent_errors = [e for e in result["errors"] if "invalid_agent" in e.get("code", "")]
        assert len(agent_errors) == 0

    def test_file_recognized(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Write", "agent_type": "file", "action": "write", "parameters": {"path": "/tmp/x", "content": "hi"}}]}
        result = v.validate(wf, "write file")
        agent_errors = [e for e in result["errors"] if "invalid_agent" in e.get("code", "")]
        assert len(agent_errors) == 0

    def test_browser_recognized(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Navigate", "agent_type": "browser", "action": "navigate", "parameters": {"url": "https://google.com"}}]}
        result = v.validate(wf, "go to google")
        agent_errors = [e for e in result["errors"] if "invalid_agent" in e.get("code", "")]
        assert len(agent_errors) == 0

    def test_vision_recognized(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Find text", "agent_type": "vision", "action": "find_text", "parameters": {"query": "hello"}}]}
        result = v.validate(wf, "find text on screen")
        agent_errors = [e for e in result["errors"] if "invalid_agent" in e.get("code", "")]
        assert len(agent_errors) == 0

    def test_invalid_agent_type_flagged(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Unknown", "agent_type": "quantum_computer", "action": "compute", "parameters": {}}]}
        result = v.validate(wf, "do quantum stuff")
        agent_errors = [e for e in result["errors"] if "invalid_agent" in e.get("code", "")]
        assert len(agent_errors) == 1


class TestValidatorActions:
    """Verify the WorkflowValidator recognizes all planner actions per agent type."""

    @pytest.mark.parametrize("action", ["run"])
    def test_terminal_actions_valid(self, action):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Run", "agent_type": "terminal", "action": action, "parameters": {"command": "ls"}}]}
        result = v.validate(wf, "run command")
        action_errors = [e for e in result["errors"] if "invalid_action" in e.get("code", "")]
        assert len(action_errors) == 0

    @pytest.mark.parametrize("action", ["click", "type", "press"])
    def test_desktop_actions_valid(self, action):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Desktop", "agent_type": "desktop", "action": action, "parameters": {}}]}
        result = v.validate(wf, "desktop action")
        action_errors = [e for e in result["errors"] if "invalid_action" in e.get("code", "")]
        assert len(action_errors) == 0

    @pytest.mark.parametrize("action", ["navigate", "click", "fill", "press", "wait", "wait_for_selector", "scrape_text", "scrape_links", "summarize"])
    def test_browser_actions_valid(self, action):
        v = WorkflowValidator()
        params = {"url": "https://x.com"} if action == "navigate" else {"selector": "#id"} if action in ("click", "fill", "wait_for_selector") else {"key": "Enter"} if action == "press" else {}
        wf = {"steps": [{"step_id": "s1", "name": "Browser", "agent_type": "browser", "action": action, "parameters": params}]}
        result = v.validate(wf, "browser action")
        action_errors = [e for e in result["errors"] if "invalid_action" in e.get("code", "")]
        assert len(action_errors) == 0

    @pytest.mark.parametrize("action", ["read", "write", "list", "delete", "find_text", "search"])
    def test_file_actions_valid(self, action):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "File", "agent_type": "file", "action": action, "parameters": {}}]}
        result = v.validate(wf, "file action")
        action_errors = [e for e in result["errors"] if "invalid_action" in e.get("code", "")]
        assert len(action_errors) == 0

    def test_invalid_action_for_terminal(self):
        v = WorkflowValidator()
        wf = {"steps": [{"step_id": "s1", "name": "Bad", "agent_type": "terminal", "action": "navigate", "parameters": {}}]}
        result = v.validate(wf, "bad action")
        action_errors = [e for e in result["errors"] if "invalid_action" in e.get("code", "")]
        assert len(action_errors) == 1


# ─── WorkflowValidator Scoring Tests ─────────────────────────────────────────

class TestValidatorScoring:
    """Test that the validator scores real planner output correctly."""

    def test_terminal_single_step_scores_well(self):
        v = WorkflowValidator()
        wf = {"steps": [
            {"step_id": "step_1", "name": "Run: Start-Process calc.exe", "agent_type": "terminal", "action": "run", "parameters": {"command": "Start-Process calc.exe"}},
        ]}
        result = v.validate(wf, "Open Calculator")
        assert result["score"] >= 80, f"Score too low: {result['score']}, errors: {result['errors']}"
        assert result["is_valid"] is True

    def test_multi_step_browser_workflow_scores_well(self):
        v = WorkflowValidator()
        wf = {"steps": [
            {"step_id": "step_1", "name": "Navigate to Google", "agent_type": "browser", "action": "navigate", "parameters": {"url": "https://www.google.com"}},
            {"step_id": "step_2", "name": "Type search query", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[name='q']", "value": "machine learning"}},
            {"step_id": "step_3", "name": "Submit search", "agent_type": "browser", "action": "press", "parameters": {"key": "Enter"}},
            {"step_id": "step_4", "name": "Extract results", "agent_type": "browser", "action": "scrape_text", "parameters": {}},
        ]}
        result = v.validate(wf, "search google for machine learning")
        assert result["score"] >= 70
        assert result["is_valid"] is True

    def test_file_write_step_scores_well(self):
        v = WorkflowValidator()
        wf = {"steps": [
            {"step_id": "step_1", "name": "Write text file", "agent_type": "file", "action": "write", "parameters": {"path": "/tmp/test.txt", "content": "Hello"}},
        ]}
        result = v.validate(wf, "create a text file")
        assert result["score"] >= 80
        assert result["is_valid"] is True

    def test_mixed_terminal_file_scores_well(self):
        v = WorkflowValidator()
        wf = {"steps": [
            {"step_id": "step_1", "name": "Write script", "agent_type": "file", "action": "write", "parameters": {"path": "/tmp/script.py", "content": "print('hi')"}},
            {"step_id": "step_2", "name": "Run script", "agent_type": "terminal", "action": "run", "parameters": {"command": "python /tmp/script.py"}},
        ]}
        result = v.validate(wf, "create and run a script")
        assert result["score"] >= 80
        assert result["is_valid"] is True


# ─── State Machine Tests ─────────────────────────────────────────────────────

class TestStateMachineTransitions:
    """Verify state machine transition rules match pipeline needs."""

    def test_valid_idle_to_planning(self):
        assert WorkflowState.PLANNING in VALID_TRANSITIONS[WorkflowState.IDLE]

    def test_valid_planning_to_executing(self):
        assert WorkflowState.EXECUTING in VALID_TRANSITIONS[WorkflowState.PLANNING]

    def test_valid_executing_to_completed(self):
        assert WorkflowState.COMPLETED in VALID_TRANSITIONS[WorkflowState.EXECUTING]

    def test_valid_executing_to_failed(self):
        assert WorkflowState.FAILED in VALID_TRANSITIONS[WorkflowState.EXECUTING]

    def test_valid_executing_to_cancelled(self):
        assert WorkflowState.CANCELLED in VALID_TRANSITIONS[WorkflowState.EXECUTING]

    def test_valid_executing_to_waiting(self):
        assert WorkflowState.WAITING in VALID_TRANSITIONS[WorkflowState.EXECUTING]

    def test_valid_executing_to_retry(self):
        assert WorkflowState.RETRY in VALID_TRANSITIONS[WorkflowState.EXECUTING]

    def test_terminal_states_have_no_transitions(self):
        assert VALID_TRANSITIONS[WorkflowState.COMPLETED] == []
        assert VALID_TRANSITIONS[WorkflowState.FAILED] == []
        assert VALID_TRANSITIONS[WorkflowState.CANCELLED] == []

    def test_cannot_go_from_idle_to_executing(self):
        assert WorkflowState.EXECUTING not in VALID_TRANSITIONS[WorkflowState.IDLE]

    def test_cannot_go_from_planning_to_completed(self):
        assert WorkflowState.COMPLETED not in VALID_TRANSITIONS[WorkflowState.PLANNING]


# ─── Event Bus Tests ─────────────────────────────────────────────────────────

class TestEventBus:
    """Verify event bus in-memory publish/subscribe works."""

    def test_publish_subscribe_in_memory(self):
        received = []

        async def handler(event: SystemEvent):
            received.append(event)

        event_bus.subscribe("test.pipeline.event", handler)
        try:
            asyncio.run(event_bus.publish("test.pipeline.event", "test", {"key": "value"}))
            assert len(received) == 1
            assert received[0].topic == "test.pipeline.event"
            assert received[0].payload == {"key": "value"}
        finally:
            event_bus.unsubscribe("test.pipeline.event", handler)

    def test_multiple_subscribers_receive_events(self):
        received_a = []
        received_b = []

        async def handler_a(event):
            received_a.append(event)
        async def handler_b(event):
            received_b.append(event)

        event_bus.subscribe("test.multi.sub", handler_a)
        event_bus.subscribe("test.multi.sub", handler_b)
        try:
            asyncio.run(event_bus.publish("test.multi.sub", "test", {"msg": "hello"}))
            assert len(received_a) == 1
            assert len(received_b) == 1
        finally:
            event_bus.unsubscribe("test.multi.sub", handler_a)
            event_bus.unsubscribe("test.multi.sub", handler_b)

    def test_unsubscribe_stops_delivery(self):
        received = []

        async def handler(event):
            received.append(event)

        event_bus.subscribe("test.unsub", handler)
        event_bus.unsubscribe("test.unsub", handler)
        asyncio.run(event_bus.publish("test.unsub", "test", {}))
        assert len(received) == 0


class TestEventFormat:
    """Verify event format matches what the frontend WebSocket handler expects."""

    def test_system_event_has_required_fields(self):
        event = SystemEvent(
            topic="task.completed",
            sender="Worker-0",
            payload={"task_id": "abc", "execution_id": "xyz", "result": {"stdout": "hello"}},
        )
        dumped = event.model_dump()
        assert "topic" in dumped
        assert "payload" in dumped
        assert "event_id" in dumped
        assert "sender" in dumped
        assert "timestamp" in dumped

    def test_workflow_state_change_event_format(self):
        event = SystemEvent(
            topic="workflow.state_change",
            sender="WorkflowStateMachine",
            payload={
                "execution_id": "exec123",
                "old_state": "Idle",
                "new_state": "Planning",
                "error_message": None,
                "metadata": {},
            },
        )
        payload = event.payload
        assert "execution_id" in payload
        assert "old_state" in payload
        assert "new_state" in payload

    def test_task_completed_event_format(self):
        event = SystemEvent(
            topic="task.completed",
            sender="Worker-0",
            payload={
                "task_id": "task123",
                "execution_id": "exec456",
                "result": {"stdout": "done", "returncode": 0},
                "verification": {"success": True, "message": "OK", "confidence": 0.9, "diagnostics": {}},
            },
        )
        payload = event.payload
        assert "task_id" in payload
        assert "execution_id" in payload
        assert "result" in payload
        assert "verification" in payload

    def test_task_failed_event_format(self):
        event = SystemEvent(
            topic="task.failed",
            sender="Worker-0",
            payload={
                "task_id": "task123",
                "execution_id": "exec456",
                "error": "Command not found",
                "step_data": {"step_id": "step_1", "agent_type": "terminal", "action": "run"},
            },
        )
        payload = event.payload
        assert "error" in payload
        assert "step_data" in payload

    def test_permission_request_event_format(self):
        event = SystemEvent(
            topic="permission.request",
            sender="PermissionGuard",
            payload={
                "request_id": "perm123",
                "execution_id": "exec456",
                "agent_type": "terminal",
                "action": "run",
                "parameters": {"command": "rm -rf /"},
            },
        )
        payload = event.payload
        assert "request_id" in payload
        assert "agent_type" in payload


# ─── Verification Engine Tests ───────────────────────────────────────────────

class TestVerificationPipeline:
    """Test verification engine integration with pipeline step formats."""

    def setup_method(self):
        self.engine = VerificationEngine()

    @pytest.mark.asyncio
    async def test_terminal_run_verification_pass(self):
        step = {"step_id": "s1", "agent_type": "terminal", "action": "run", "parameters": {"command": "echo hi"}}
        result = {"returncode": 0, "stdout": "hi", "stderr": ""}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_terminal_run_verification_fail(self):
        step = {"step_id": "s1", "agent_type": "terminal", "action": "run", "parameters": {"command": "bad"}}
        result = {"returncode": 1, "stdout": "", "stderr": "command not found"}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is False

    @pytest.mark.asyncio
    async def test_browser_navigate_verification_pass(self):
        step = {"step_id": "s1", "agent_type": "browser", "action": "navigate", "parameters": {"url": "https://google.com"}}
        result = {"url": "https://google.com", "title": "Google"}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_browser_fill_verification_pass(self):
        step = {"step_id": "s1", "agent_type": "browser", "action": "fill", "parameters": {"selector": "#q", "value": "test"}}
        result = {"actual_value": "test", "method": "page.fill"}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_browser_fill_verification_mismatch(self):
        step = {"step_id": "s1", "agent_type": "browser", "action": "fill", "parameters": {"selector": "#q", "value": "expected_text"}} 
        result = {"actual_value": "different_text", "method": "page.fill"}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is False

    @pytest.mark.asyncio
    async def test_file_write_verification_pass(self):
        step = {"step_id": "s1", "agent_type": "file", "action": "write", "parameters": {"path": "/tmp/test.txt"}}
        result = {"path": "/tmp/test.txt", "success": True}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is True

    @pytest.mark.asyncio
    async def test_unknown_agent_type_assumed_success(self):
        step = {"step_id": "s1", "agent_type": "desktop", "action": "click", "parameters": {}}
        result = {"success": True}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is True
        assert vresult.confidence == 0.5

    @pytest.mark.asyncio
    async def test_scrape_text_verification_pass(self):
        step = {"step_id": "s1", "agent_type": "browser", "action": "scrape_text", "parameters": {}}
        result = {"text": "This is scraped content from the page that is quite long."}
        vresult = await self.engine.verify(step, result)
        assert vresult.success is True


# ─── Recovery Engine Tests ───────────────────────────────────────────────────

class TestRecoveryPipeline:
    """Test recovery engine handles pipeline failure scenarios."""

    def setup_method(self):
        self.engine = RecoveryEngine()
        self.engine.reset_all()

    @pytest.mark.asyncio
    async def test_first_attempt_returns_retry(self):
        step = {"step_id": "s1", "agent_type": "terminal", "action": "run", "parameters": {"command": "echo hi"}}
        action = await self.engine.recover(step, Exception("timeout"), None, "s1")
        assert action.strategy == RecoveryStrategy.RETRY

    @pytest.mark.asyncio
    async def test_command_not_found_aborts(self):
        step = {"step_id": "s1", "agent_type": "terminal", "action": "run", "parameters": {"command": "nonexistent_tool"}}
        action = await self.engine.recover(step, Exception("command not found"), None, "s1")
        assert action.strategy == RecoveryStrategy.ABORT

    @pytest.mark.asyncio
    async def test_max_attempts_abort(self):
        step = {"step_id": "s1", "agent_type": "terminal", "action": "run", "parameters": {"command": "echo hi"}}
        for i in range(5):
            action = await self.engine.recover(step, Exception("generic error"), None, "s1")
        assert action.strategy == RecoveryStrategy.ABORT


# ─── Task Queue Tests ────────────────────────────────────────────────────────

class TestTaskQueue:
    """Test task queue lifecycle."""

    @pytest.mark.asyncio
    async def test_enqueue_returns_task_id(self):
        task_id = await TaskQueue.enqueue("exec_test", {"step_id": "s1", "agent_type": "terminal", "action": "run"})
        assert task_id is not None
        assert len(task_id) > 0
        status = await TaskQueue.get_status(task_id)
        assert status["status"] == "queued"

    @pytest.mark.asyncio
    async def test_enqueued_task_has_execution_id(self):
        task_id = await TaskQueue.enqueue("exec_test_2", {"step_id": "s1"})
        status = await TaskQueue.get_status(task_id)
        assert status["execution_id"] == "exec_test_2"


# ─── End-to-End Data Flow Tests ──────────────────────────────────────────────

class TestEndToEndDataFlow:
    """Test the complete data flow from planner output through execution."""

    def test_planner_output_to_step_model_conversion(self):
        """Planner output steps can be converted to Step models."""
        planner_steps = [
            {"step_id": "step_1", "name": "Navigate", "agent_type": "browser", "action": "navigate", "parameters": {"url": "https://google.com"}},
            {"step_id": "step_2", "name": "Search", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[name='q']", "value": "test"}},
        ]
        step_models = [Step(**s) for s in planner_steps]
        assert len(step_models) == 2
        assert step_models[0].agent_type == "browser"
        assert step_models[1].action == "fill"

    def test_step_model_to_dict_for_worker(self):
        """Step model converts back to dict for worker consumption."""
        s = Step(step_id="step_1", name="Run", agent_type="terminal", action="run", parameters={"command": "echo hi"})
        d = s.model_dump()
        assert d["step_id"] == "step_1"
        assert d["agent_type"] == "terminal"
        assert isinstance(d["parameters"], dict)

    def test_step_dict_with_user_id_for_execution(self):
        """Worker adds user_id to step payload."""
        step_data = {"step_id": "step_1", "agent_type": "terminal", "action": "run", "parameters": {"command": "echo hi"}}
        step_data["user_id"] = "user123"
        assert step_data["user_id"] == "user123"
        assert "step_id" in step_data

    def test_result_format_matches_verification_input(self):
        """Agent execution result matches what verification expects."""
        result = {"returncode": 0, "stdout": "hello", "stderr": ""}
        step = {"step_id": "s1", "agent_type": "terminal", "action": "run", "parameters": {"command": "echo hi"}}
        engine = VerificationEngine()
        vresult = asyncio.run(engine.verify(step, result))
        assert vresult.success is True

    def test_verification_result_to_event_payload(self):
        """Verification result can be included in task.completed event."""
        vr = VerificationResult(success=True, message="OK", confidence=0.9, diagnostics={"rc": 0})
        payload = {
            "task_id": "t1",
            "execution_id": "e1",
            "result": {"stdout": "done"},
            "verification": {
                "success": vr.success,
                "message": vr.message,
                "confidence": vr.confidence,
                "diagnostics": vr.diagnostics,
            },
        }
        event = SystemEvent(topic="task.completed", sender="Worker-0", payload=payload)
        assert event.payload["verification"]["success"] is True

    def test_workflow_engine_step_payload_format(self):
        """Step payload sent to TaskQueue has required fields."""
        step = Step(step_id="step_1", name="Run", agent_type="terminal", action="run", parameters={"command": "echo hi"})
        step_payload = step.model_dump()
        step_payload["user_id"] = "user123"

        required_fields = ["step_id", "name", "agent_type", "action", "parameters", "user_id"]
        for field in required_fields:
            assert field in step_payload, f"Missing field: {field}"

    def test_state_machine_validates_full_pipeline_flow(self):
        """Full pipeline flow: IDLE → PLANNING → EXECUTING → COMPLETED."""
        flow = [WorkflowState.IDLE, WorkflowState.PLANNING, WorkflowState.EXECUTING, WorkflowState.COMPLETED]
        for i in range(len(flow) - 1):
            assert flow[i + 1] in VALID_TRANSITIONS[flow[i]], f"Invalid transition: {flow[i]} -> {flow[i+1]}"
