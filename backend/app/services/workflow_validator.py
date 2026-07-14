from typing import Dict, Any, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

AGENT_TYPES = {
    "browser", "browser_agent",
    "terminal",
    "file", "filesystem", "file_system", "file_system_agent",
    "desktop", "computer", "computer_agent",
    "application", "application_agent",
    "messaging", "messaging_agent",
    "media", "media_agent",
    "email", "email_agent",
    "calendar", "calendar_agent",
    "ai_assistant", "ai_assistant_agent",
    "vision",
}

BROWSER_ACTIONS = {"navigate", "click", "fill", "press", "wait", "wait_for_selector", "scrape_text", "scrape_links", "summarize", "search", "type", "scroll", "select", "open", "close"}
TERMINAL_ACTIONS = {"run"}
FILE_ACTIONS = {"read", "write", "list", "delete", "find_text", "search"}
DESKTOP_ACTIONS = {"click", "type", "press"}
APPLICATION_ACTIONS = {"open", "close", "focus", "minimize", "maximize"}
COMPUTER_ACTIONS = {"screenshot", "mouse_click", "mouse_move", "type_text", "press_key", "hotkey", "scroll"}
MESSAGING_ACTIONS = {"send_message", "create_channel", "read_message"}
MEDIA_ACTIONS = {"play", "pause", "stop", "next", "previous", "volume_up", "volume_down"}
VISION_ACTIONS = {"find_text", "capture_elements"}

AGENT_ACTIONS: Dict[str, set] = {
    "browser": BROWSER_ACTIONS, "browser_agent": BROWSER_ACTIONS,
    "terminal": TERMINAL_ACTIONS,
    "file": FILE_ACTIONS, "filesystem": FILE_ACTIONS, "file_system": FILE_ACTIONS, "file_system_agent": FILE_ACTIONS,
    "desktop": DESKTOP_ACTIONS, "computer": COMPUTER_ACTIONS, "computer_agent": COMPUTER_ACTIONS,
    "application": APPLICATION_ACTIONS, "application_agent": APPLICATION_ACTIONS,
    "messaging": MESSAGING_ACTIONS, "messaging_agent": MESSAGING_ACTIONS,
    "media": MEDIA_ACTIONS, "media_agent": MEDIA_ACTIONS,
    "email": {"send", "read", "search", "compose", "reply"}, "email_agent": {"send", "read", "search", "compose", "reply"},
    "calendar": {"create", "read", "update", "delete"}, "calendar_agent": {"create", "read", "update", "delete"},
    "ai_assistant": {"generate", "analyze", "summarize"}, "ai_assistant_agent": {"generate", "analyze", "summarize"},
    "vision": VISION_ACTIONS,
}

VAGUE_ACTIONS = {"do_something", "handle", "process", "execute", "perform", "run_task", "task", "action", "step", "do", "make", "setup"}
VAGUE_NAMES = {"step", "task", "action", "item", "thing", "process", "do_something", "handle", "process_data"}


class WorkflowValidationError:
    def __init__(self, code: str, message: str, severity: str = "error", step_id: Optional[str] = None):
        self.code = code
        self.message = message
        self.severity = severity
        self.step_id = step_id

    def to_dict(self) -> Dict[str, Any]:
        result = {"code": self.code, "message": self.message, "severity": self.severity}
        if self.step_id:
            result["step_id"] = self.step_id
        return result


class WorkflowValidator:
    def __init__(self, min_quality_score: int = 70):
        self.min_quality_score = min_quality_score
        self._checks: List[Tuple[str, Any, int]] = []
        self._errors: List[WorkflowValidationError] = []

    def validate(self, workflow: Dict[str, Any], user_prompt: str = "") -> Dict[str, Any]:
        self._checks = []
        self._errors = []
        self._run_all_checks(workflow, user_prompt)
        score = self._calculate_score()
        passed = [name for name, _, _ in self._checks if not any(e.code.startswith(name) for e in self._errors)]
        failed = [name for name, _, _ in self._checks if any(e.code.startswith(name) for e in self._errors)]
        is_valid = score >= self.min_quality_score and not any(e.severity == "error" for e in self._errors)
        return {
            "is_valid": is_valid,
            "score": score,
            "min_required": self.min_quality_score,
            "passed": len(passed),
            "failed": len(failed),
            "errors": [e.to_dict() for e in self._errors],
            "summary": self._build_summary(score, is_valid, passed, failed),
        }

    def validate_schema(self, workflow: Dict[str, Any]) -> List[WorkflowValidationError]:
        errors: List[WorkflowValidationError] = []
        steps = workflow.get("steps")
        if steps is None:
            errors.append(WorkflowValidationError("schema.missing_steps", "Workflow has no 'steps' field.", "error"))
            return errors
        if not isinstance(steps, list):
            errors.append(WorkflowValidationError("schema.invalid_steps_type", "Workflow 'steps' must be a list.", "error"))
            return errors
        for i, step in enumerate(steps):
            step_id = step.get("step_id", f"step_{i}")
            if not isinstance(step, dict):
                errors.append(WorkflowValidationError("schema.invalid_step_type", f"Step {i} is not a dict.", "error", step_id))
                continue
            for field in ["step_id", "name", "agent_type", "action"]:
                if not step.get(field):
                    errors.append(WorkflowValidationError("schema.missing_field", f"Step missing required field '{field}'.", "error", step_id))
        return errors

    def _run_all_checks(self, workflow: Dict[str, Any], user_prompt: str):
        schema_errors = self.validate_schema(workflow)
        self._errors.extend(schema_errors)
        steps = workflow.get("steps", [])
        if not steps or schema_errors:
            self._checks.append(("completeness", lambda: False, 0))
            return
        self._checks.append(("structure", self._check_structure, 1))
        self._check_structure(workflow, user_prompt)
        self._checks.append(("quality", self._check_quality, 1))
        self._check_quality(workflow, user_prompt)
        self._checks.append(("dependencies", self._check_dependencies, 1))
        self._check_dependencies(workflow)
        self._checks.append(("completeness", self._check_completeness, 1))
        self._check_completeness(workflow, user_prompt)
        self._checks.append(("vague_actions", self._check_vague_actions, 1))
        self._check_vague_actions(workflow)
        self._checks.append(("duplicates", self._check_duplicates, 1))
        self._check_duplicates(workflow)
        self._checks.append(("verification", self._check_verification_step, 1))
        self._check_verification_step(workflow)

    def _check_structure(self, workflow: Dict[str, Any], user_prompt: str):
        steps = workflow.get("steps", [])
        valid_agents = set()
        for _ in range(len(steps)):
            valid_agents.add(True)
        for i, step in enumerate(steps):
            agent_type = step.get("agent_type", "")
            action = step.get("action", "")
            valid = True
            if agent_type not in AGENT_TYPES:
                self._errors.append(WorkflowValidationError(
                    "structure.invalid_agent", f"Unsupported agent type: '{agent_type}'.", "error", step.get("step_id")
                ))
                valid = False
            if valid and agent_type in AGENT_ACTIONS:
                if action not in AGENT_ACTIONS[agent_type]:
                    self._errors.append(WorkflowValidationError(
                        "structure.invalid_action", f"Action '{action}' not supported for agent '{agent_type}'.", "error", step.get("step_id")
                    ))
            if not step.get("name"):
                self._errors.append(WorkflowValidationError(
                    "structure.empty_name", f"Step {i+1} has no name.", "warning", step.get("step_id")
                ))

    def _check_quality(self, workflow: Dict[str, Any], user_prompt: str):
        steps = workflow.get("steps", [])
        if len(steps) > 10:
            self._errors.append(WorkflowValidationError(
                "quality.too_many_steps", f"Workflow has {len(steps)} steps (max recommended: 10).", "warning"
            ))
        for i, step in enumerate(steps):
            params = step.get("parameters", {})
            if isinstance(params, dict):
                if step.get("agent_type") in AGENT_TYPES and step.get("action"):
                    required_params = self._get_required_params(step["agent_type"], step["action"])
                    for rp in required_params:
                        if rp not in params:
                            self._errors.append(WorkflowValidationError(
                                "quality.missing_param", f"Step {i+1} missing recommended parameter '{rp}'.", "warning", step.get("step_id")
                            ))

    def _check_dependencies(self, workflow: Dict[str, Any]):
        steps = workflow.get("steps", [])
        step_ids = set()
        for step in steps:
            sid = step.get("step_id", "")
            if sid in step_ids:
                self._errors.append(WorkflowValidationError(
                    "dependencies.duplicate_id", f"Duplicate step ID: '{sid}'.", "error", sid
                ))
            step_ids.add(sid)
        for step in steps:
            depends_on = step.get("depends_on", [])
            if isinstance(depends_on, str):
                depends_on = [depends_on]
            for dep_id in depends_on:
                if dep_id not in step_ids:
                    self._errors.append(WorkflowValidationError(
                        "dependencies.invalid_ref", f"Step references non-existent dependency '{dep_id}'.", "error", step.get("step_id")
                    ))

    def _check_completeness(self, workflow: Dict[str, Any], user_prompt: str):
        steps = workflow.get("steps", [])
        if not user_prompt:
            return
        prompt_lower = user_prompt.lower()
        if any(w in prompt_lower for w in ["email", "send mail", "write to"]) and not any(
            s.get("agent_type") in ("email", "email_agent", "browser") for s in steps
        ):
            self._errors.append(WorkflowValidationError(
                "completeness.missing_email", "Prompt mentions email but no email agent in workflow.", "warning"
            ))
        if any(w in prompt_lower for w in ["file", "save", "read", "write", "create"]) and not any(
            s.get("agent_type") in ("file", "filesystem", "file_system", "file_system_agent", "terminal") for s in steps
        ):
            self._errors.append(WorkflowValidationError(
                "completeness.missing_filesystem", "Prompt mentions file operations but no filesystem agent.", "warning"
            ))

    def _check_vague_actions(self, workflow: Dict[str, Any]):
        steps = workflow.get("steps", [])
        for step in steps:
            action = step.get("action", "").lower()
            name = step.get("name", "").lower()
            if action in VAGUE_ACTIONS:
                self._errors.append(WorkflowValidationError(
                    "vague_actions.vague_action", f"Step uses vague action: '{action}'.", "error", step.get("step_id")
                ))
            if name in VAGUE_NAMES:
                self._errors.append(WorkflowValidationError(
                    "vague_actions.vague_name", f"Step uses vague name: '{name}'.", "warning", step.get("step_id")
                ))

    def _check_duplicates(self, workflow: Dict[str, Any]):
        steps = workflow.get("steps", [])
        seen = set()
        for step in steps:
            key = (step.get("agent_type", ""), step.get("action", ""), str(sorted(step.get("parameters", {}).items())))
            if key in seen:
                self._errors.append(WorkflowValidationError(
                    "duplicates.duplicate_step", f"Duplicate step: '{step.get('name', 'unnamed')}'.", "warning", step.get("step_id")
                ))
            seen.add(key)

    def _check_verification_step(self, workflow: Dict[str, Any]):
        steps = workflow.get("steps", [])
        if len(steps) >= 3:
            last_step = steps[-1]
            if last_step.get("agent_type") != "computer" and last_step.get("action") != "screenshot":
                self._errors.append(WorkflowValidationError(
                    "verification.no_verification", "No verification step (screenshot) at end of multi-step workflow.", "warning"
                ))

    def _get_required_params(self, agent_type: str, action: str) -> List[str]:
        requirements = {
            ("browser", "navigate"): ["url"],
            ("browser", "click"): ["selector"],
            ("browser", "fill"): ["selector", "value"],
            ("browser", "scrape_text"): [],
            ("browser", "scrape_links"): [],
            ("browser", "summarize"): ["query"],
            ("terminal", "run"): ["command"],
            ("file", "read"): ["path"],
            ("file", "write"): ["path", "content"],
            ("file", "list"): [],
            ("file", "find_text"): ["query"],
            ("desktop", "click"): ["target"],
            ("desktop", "type"): ["text"],
            ("desktop", "press"): ["key"],
            ("application", "open"): ["app_name"],
            ("computer", "type_text"): ["text"],
            ("computer", "press_key"): ["key"],
            ("email", "send"): ["to", "subject"],
            ("messaging", "send_message"): ["message"],
        }
        return requirements.get((agent_type, action), [])

    def _calculate_score(self) -> int:
        if not self._checks:
            return 0
        total_weight = sum(w for _, _, w in self._checks)
        if total_weight == 0:
            return 0
        error_counts = {}
        for e in self._errors:
            prefix = e.code.split(".")[0]
            error_counts[prefix] = error_counts.get(prefix, 0) + 1
        deductions = 0
        for prefix, count in error_counts.items():
            if prefix in ("structure", "schema"):
                deductions += count * 15
            elif prefix == "vague_actions":
                deductions += count * 20
            elif prefix == "duplicates":
                deductions += count * 10
            elif prefix == "dependencies":
                deductions += count * 15
            else:
                deductions += count * 5
        return max(0, min(100, 100 - deductions))

    def _build_summary(self, score: int, is_valid: bool, passed: List[str], failed: List[str]) -> str:
        if is_valid:
            return f"Workflow passed quality checks (score: {score}/100). {len(passed)} checks passed."
        parts = [f"Workflow failed quality checks (score: {score}/100, min required: {self.min_quality_score})."]
        if failed:
            parts.append(f"Failed checks: {', '.join(failed)}.")
        if self._errors:
            error_msgs = [e.message for e in self._errors if e.severity == "error"]
            if error_msgs:
                parts.append("Critical issues: " + "; ".join(error_msgs[:3]))
        return " ".join(parts)


validator = WorkflowValidator()
