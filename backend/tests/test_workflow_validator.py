import pytest
from app.services.workflow_validator import WorkflowValidator, WorkflowValidationError


@pytest.fixture
def validator():
    return WorkflowValidator(min_quality_score=70)


def _make_step(step_id="step_1", name="Open browser", agent_type="browser", action="navigate", parameters=None):
    return {
        "step_id": step_id,
        "name": name,
        "agent_type": agent_type,
        "action": action,
        "parameters": parameters or {},
    }


class TestWorkflowValidatorSchema:
    def test_valid_workflow_passes(self, validator):
        wf = {"steps": [_make_step(parameters={"url": "https://google.com"}), _make_step("step_2", "Search", "browser", "search", {"query": "test"})]}
        result = validator.validate(wf, "search for test")
        assert result["is_valid"] is True
        assert result["score"] >= 70

    def test_missing_steps_returns_zero(self, validator):
        result = validator.validate({}, "test")
        assert result["is_valid"] is False
        assert result["score"] == 0

    def test_steps_not_list_returns_zero(self, validator):
        result = validator.validate({"steps": "not a list"}, "test")
        assert result["is_valid"] is False

    def test_missing_step_id(self, validator):
        wf = {"steps": [{"name": "Test", "agent_type": "browser", "action": "navigate"}]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "schema.missing_field" for e in result["errors"])

    def test_missing_agent_type(self, validator):
        wf = {"steps": [{"step_id": "step_1", "name": "Test", "action": "navigate"}]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "schema.missing_field" for e in result["errors"])

    def test_missing_action(self, validator):
        wf = {"steps": [{"step_id": "step_1", "name": "Test", "agent_type": "browser"}]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "schema.missing_field" for e in result["errors"])

    def test_missing_name(self, validator):
        wf = {"steps": [{"step_id": "step_1", "agent_type": "browser", "action": "navigate"}]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "schema.missing_field" for e in result["errors"])


class TestWorkflowValidatorAgentActions:
    def test_invalid_agent_type(self, validator):
        wf = {"steps": [_make_step(agent_type="nonexistent_agent")]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "structure.invalid_agent" for e in result["errors"])

    def test_invalid_action_for_agent(self, validator):
        wf = {"steps": [_make_step(agent_type="browser", action="delete")]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "structure.invalid_action" for e in result["errors"])

    def test_valid_browser_actions(self, validator):
        for action in ["navigate", "click", "search", "type", "scroll"]:
            wf = {"steps": [_make_step(agent_type="browser", action=action)]}
            result = validator.validate(wf, "test")
            assert not any(e["code"] == "structure.invalid_action" for e in result["errors"])


class TestWorkflowValidatorVague:
    def test_vague_action_detected(self, validator):
        wf = {"steps": [_make_step(action="do_something")]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "vague_actions.vague_action" for e in result["errors"])

    def test_vague_name_detected(self, validator):
        wf = {"steps": [_make_step(name="step")]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "vague_actions.vague_name" for e in result["errors"])


class TestWorkflowValidatorDuplicates:
    def test_duplicate_step_ids(self, validator):
        wf = {"steps": [_make_step("step_1", "A"), _make_step("step_1", "B")]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "dependencies.duplicate_id" for e in result["errors"])

    def test_duplicate_steps_detected(self, validator):
        s = _make_step(agent_type="browser", action="search", parameters={"query": "x"})
        wf = {"steps": [s, _make_step("step_2", "B", "browser", "search", {"query": "x"})]}
        result = validator.validate(wf, "test")
        assert any(e["code"] == "duplicates.duplicate_step" for e in result["errors"])


class TestWorkflowValidatorDependencies:
    def test_invalid_dependency_reference(self, validator):
        wf = {"steps": [_make_step("step_1"), _make_step("step_2")]}
        wf["steps"][1]["depends_on"] = ["step_99"]
        result = validator.validate(wf, "test")
        assert any(e["code"] == "dependencies.invalid_ref" for e in result["errors"])


class TestWorkflowValidatorCompleteness:
    def test_email_prompt_missing_email_agent(self, validator):
        wf = {"steps": [_make_step(agent_type="terminal", action="run")]}
        result = validator.validate(wf, "send an email to john@example.com")
        assert any(e["code"] == "completeness.missing_email" for e in result["errors"])

    def test_file_prompt_missing_filesystem_agent(self, validator):
        wf = {"steps": [_make_step(agent_type="browser", action="navigate")]}
        result = validator.validate(wf, "read the file report.txt")
        assert any(e["code"] == "completeness.missing_filesystem" for e in result["errors"])


class TestWorkflowValidatorVerification:
    def test_no_verification_step_warning(self, validator):
        steps = [_make_step(f"step_{i}", f"Step {i}", "browser", "click") for i in range(1, 5)]
        wf = {"steps": steps}
        result = validator.validate(wf, "do many things")
        assert any(e["code"] == "verification.no_verification" for e in result["errors"])


class TestWorkflowValidatorScore:
    def test_perfect_workflow_scores_high(self, validator):
        wf = {
            "steps": [
                _make_step("step_1", "Navigate to Google", "browser", "navigate", {"url": "https://google.com"}),
                _make_step("step_2", "Take screenshot", "computer", "screenshot"),
            ]
        }
        result = validator.validate(wf, "open google")
        assert result["score"] >= 80

    def test_many_errors_low_score(self, validator):
        wf = {"steps": [
            {"step_id": "step_1", "name": "do", "agent_type": "invalid", "action": "do_something"},
            {"step_id": "step_1", "name": "step", "agent_type": "another_invalid", "action": "handle"},
        ]}
        result = validator.validate(wf, "test")
        assert result["score"] < 50

    def test_empty_workflow_zero_score(self, validator):
        result = validator.validate({"steps": []}, "test")
        assert result["score"] == 0
