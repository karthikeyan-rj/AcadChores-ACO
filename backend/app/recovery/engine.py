import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    ALTERNATIVE_SELECTOR = "alternative_selector"
    ALTERNATIVE_TOOL = "alternative_tool"
    ALTERNATIVE_AGENT = "alternative_agent"
    ASK_USER = "ask_user"
    ABORT = "abort"


@dataclass
class RecoveryAction:
    strategy: RecoveryStrategy
    modified_step: Optional[Dict[str, Any]] = None
    message: str = ""
    delay_seconds: float = 1.0


RECOVERY_PIPELINE = [
    RecoveryStrategy.RETRY,
    RecoveryStrategy.ALTERNATIVE_SELECTOR,
    RecoveryStrategy.ALTERNATIVE_TOOL,
    RecoveryStrategy.ALTERNATIVE_AGENT,
    RecoveryStrategy.ASK_USER,
    RecoveryStrategy.ABORT,
]


class RecoveryEngine:
    def __init__(self):
        self._attempts: Dict[str, int] = {}
        self._max_tracked_steps = 200

    def get_attempts(self, step_id: str) -> int:
        return self._attempts.get(step_id, 0)

    def _cleanup_old_attempts(self):
        """Evict oldest entries if dict grows too large."""
        if len(self._attempts) > self._max_tracked_steps:
            keys = list(self._attempts.keys())
            for k in keys[: len(keys) // 2]:
                self._attempts.pop(k, None)

    async def recover(
        self,
        step: Dict[str, Any],
        error: Optional[Exception],
        verification_result: Any,
        step_id: str,
    ) -> RecoveryAction:
        attempt = self._attempts.get(step_id, 0) + 1
        self._attempts[step_id] = attempt
        self._cleanup_old_attempts()

        agent_type = step.get("agent_type", "")
        action = step.get("action", "")
        params = step.get("parameters", {})

        # Check if this is a destructive action that should not be retried
        is_destructive = self._is_destructive_action(agent_type, action, params)
        if is_destructive and attempt > 1:
            logger.warning(f"Destructive action {agent_type}/{action} failed, not retrying (attempt {attempt})")
            return RecoveryAction(
                strategy=RecoveryStrategy.ABORT,
                message=f"Destructive action {agent_type}/{action} failed after {attempt} attempts. Not retrying to prevent data loss.",
            )

        logger.info(f"Recovery attempt {attempt} for {agent_type}/{action} [{step_id}]")

        # Abort immediately for "command not found" errors — retrying won't help
        error_str = str(error).lower() if error else ""
        # Also check verification result for terminal command errors
        verif_str = ""
        if verification_result:
            if isinstance(verification_result, dict):
                verif_str = str(verification_result.get("message", "")).lower() + " " + str(verification_result.get("output", "")).lower()
            else:
                verif_str = str(verification_result).lower()
        combined = error_str + " " + verif_str
        if any(phrase in combined for phrase in [
            "is not recognized", "not found", "no such file",
            "command not found", "not installed",
        ]):
            cmd = params.get("command", "")
            return RecoveryAction(
                strategy=RecoveryStrategy.ABORT,
                message=f"Command not available: {cmd}. Install the required tool and try again.",
            )

        if attempt == 1:
            return RecoveryAction(
                strategy=RecoveryStrategy.RETRY,
                modified_step=dict(step),
                message=f"Retry #{attempt}: {agent_type}/{action}",
                delay_seconds=1.0,
            )

        if attempt == 2 and action in ("click", "fill"):
            selector = params.get("selector", "")
            if selector:
                alt = self._generate_alternative_selector(selector)
                modified = dict(step)
                modified["parameters"] = dict(params)
                modified["parameters"]["selector"] = alt
                return RecoveryAction(
                    strategy=RecoveryStrategy.ALTERNATIVE_SELECTOR,
                    modified_step=modified,
                    message=f"Trying alternative selector: {alt}",
                    delay_seconds=0.5,
                )

        if attempt == 3 and action == "click":
            fallback_text = params.get("fallback_text", "")
            if fallback_text:
                modified = dict(step)
                modified["parameters"] = dict(params)
                modified["parameters"]["selector"] = f"text={fallback_text}"
                return RecoveryAction(
                    strategy=RecoveryStrategy.ALTERNATIVE_TOOL,
                    modified_step=modified,
                    message=f"Trying text-based click: '{fallback_text}'",
                    delay_seconds=0.5,
                )

        if attempt == 4 and agent_type == "browser":
            if action == "fill":
                import httpx
                from app.core.config import settings
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        response = await client.post(
                            f"{settings.OLLAMA_BASE_URL}/api/generate",
                            json={
                                "model": settings.OLLAMA_MODEL,
                                "prompt": f"Given the error: {verification_result.message if hasattr(verification_result, 'message') else error}. What's an alternative way to perform the action '{action}' with parameters {params}? Return only a JSON with 'selector' field.",
                                "stream": False,
                                "options": {"temperature": 0.1},
                            },
                        )
                        if response.status_code == 200:
                            import json as j
                            text = response.json().get("response", "")
                            try:
                                if "```" in text:
                                    text = text.split("```")[1]
                                    if text.startswith("json"):
                                        text = text[4:]
                                alt_params = j.loads(text.strip())
                                modified = dict(step)
                                modified["parameters"] = dict(params)
                                modified["parameters"].update(alt_params)
                                return RecoveryAction(
                                    strategy=RecoveryStrategy.ALTERNATIVE_TOOL,
                                    modified_step=modified,
                                    message=f"LLM suggested alternative params",
                                    delay_seconds=1.0,
                                )
                            except Exception:
                                pass
                except Exception:
                    pass

        if attempt >= 5:
            return RecoveryAction(
                strategy=RecoveryStrategy.ABORT,
                message=f"Exhausted {attempt} recovery attempts for {agent_type}/{action}",
            )

        return RecoveryAction(
            strategy=RecoveryStrategy.RETRY,
            modified_step=dict(step),
            message=f"Retry #{attempt}",
            delay_seconds=1.0,
        )

    def _is_destructive_action(self, agent_type: str, action: str, params: Dict[str, Any]) -> bool:
        """Check if an action is destructive and should not be retried."""
        # File deletion
        if agent_type == "file" and action == "delete":
            return True
        # Terminal delete commands
        if agent_type == "terminal" and action == "run":
            cmd = params.get("command", "").lower()
            delete_patterns = ["remove-item", "del ", "del/", "rm ", "rm -", "rmdir", "erase ", "unlink"]
            if any(pattern in cmd for pattern in delete_patterns):
                return True
        # File move/rename (could overwrite)
        if agent_type == "file" and action in ("move", "rename", "move_matching"):
            return True
        return False

    def reset_attempts(self, step_id: str) -> None:
        self._attempts.pop(step_id, None)

    def reset_all(self) -> None:
        self._attempts.clear()

    def _generate_alternative_selector(self, selector: str) -> str:
        alternatives = selector.split(",")
        if len(alternatives) > 1:
            used = alternatives[0].strip()
            remaining = [a.strip() for a in alternatives[1:]]
            return remaining[0] if remaining else used
        import re
        # CSS → XPath-like via aria-label
        aria_match = re.search(r"\[aria-label=['\"]*(.+?)['\"]*\]", selector)
        if aria_match:
            label = aria_match.group(1)
            return f"[title='{label}']"
        # input[name='q'] → textarea[name='q']
        name_match = re.search(r"\[name=['\"](\w+)['\"]\]", selector)
        if name_match:
            name = name_match.group(1)
            return f"textarea[name='{name}'], input[name='{name}']"
        return selector


recovery_engine = RecoveryEngine()
