import os
import json
import re
import logging
import sys
import asyncio
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from langgraph.graph import StateGraph, END

from app.ai import llm_service
from app.services.language_engine import (
    LanguageDetector, ExtensionResolver, ExecutionDispatcher, CompilerManager, LanguageDef,
    _NAME_TO_DEF,
)

logger = logging.getLogger(__name__)

# Resolve actual Windows user folders (handles OneDrive redirection)
_USER_DIRS: Dict[str, str] = {}

def _resolve_user_dirs() -> Dict[str, str]:
    """Read real Desktop/Documents/Downloads paths from Windows registry, fall back to default."""
    if _USER_DIRS:
        return _USER_DIRS
    home = os.path.expanduser("~")
    defaults = {
        "desktop": os.path.join(home, "Desktop"),
        "documents": os.path.join(home, "Documents"),
        "downloads": os.path.join(home, "Downloads"),
        "pictures": os.path.join(home, "Pictures"),
        "music": os.path.join(home, "Music"),
        "videos": os.path.join(home, "Videos"),
    }
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
            registry_map = {
                "desktop": "Desktop",
                "documents": "Personal",
                "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
                "pictures": "My Pictures",
                "music": "My Music",
                "videos": "My Video",
            }
            for folder_key, reg_name in registry_map.items():
                try:
                    val, _ = winreg.QueryValueEx(key, reg_name)
                    if val and os.path.isdir(val):
                        defaults[folder_key] = val
                except (FileNotFoundError, OSError):
                    pass
            winreg.CloseKey(key)
        except (ImportError, OSError, FileNotFoundError):
            pass
    _USER_DIRS.update(defaults)
    return _USER_DIRS

def get_user_dir(name: str) -> str:
    """Get a user directory by common name (desktop, documents, downloads, etc.)."""
    dirs = _resolve_user_dirs()
    return dirs.get(name.lower(), os.path.join(os.path.expanduser("~"), name))


# State structure for the LangGraph compilation
class PlannerState(BaseModel):
    user_prompt: str
    parsed_intent: str = ""
    steps: List[Dict[str, Any]] = []
    errors: List[str] = []
    is_valid: bool = False


_METADATA_CACHE: Dict[str, Dict[str, Any]] = {}


async def _extract_prompt_metadata(prompt: str) -> Dict[str, Any]:
    """Use LLM to extract structured metadata from a user prompt.

    Returns dict with keys: filename, target_directory, topic, language, is_code, is_destructive.
    Caches per prompt hash. Falls back to defaults on LLM failure.
    """
    import hashlib
    cache_key = hashlib.md5(prompt.strip().lower().encode()).hexdigest()
    if cache_key in _METADATA_CACHE:
        return _METADATA_CACHE[cache_key]

    defaults = {
        "filename": None,
        "target_directory": None,
        "topic": None,
        "language": None,
        "is_code": False,
        "is_destructive": False,
    }

    extraction_prompt = f"""Extract structured metadata from this user prompt. Return ONLY valid JSON, no explanation.

User prompt: "{prompt}"

Return exactly this JSON structure:
{{
  "filename": "the explicit filename if user said 'called X' or 'named X' (e.g. 'notes.txt', 'palindrome.cpp'), otherwise null",
  "target_directory": "one of 'desktop','documents','downloads','pictures','music','videos' if user specified a location, otherwise null",
  "topic": "core subject for filename generation if no explicit filename (e.g. 'palindrome', 'calculator', 'notes'), otherwise null",
  "language": "programming language if specified (e.g. 'python','cpp','javascript','java','c','go','rust'), otherwise null",
  "is_code": true if this is a code/programming request, false otherwise,
  "is_destructive": true if this is a destructive/dangerous command (delete, format, shutdown, destroy, remove all, etc.), false otherwise
}}

Rules:
- filename: only if user explicitly named the file (e.g. "called todo.txt", "named index.html")
- target_directory: only common user folders, not full paths
- topic: the main subject stripped of action words and location
- language: natural language name, not file extension
- is_destructive: anything that could cause data loss or system damage"""

    try:
        generated = await asyncio.wait_for(
            llm_service.generate(
                prompt=extraction_prompt,
                temperature=0.0,
                max_tokens=300,
            ),
            timeout=10.0,
        )
        if generated:
            text = generated.strip()
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)
            result = json.loads(text)
            metadata = {
                "filename": result.get("filename"),
                "target_directory": result.get("target_directory"),
                "topic": result.get("topic"),
                "language": result.get("language"),
                "is_code": bool(result.get("is_code")),
                "is_destructive": bool(result.get("is_destructive")),
            }
            _METADATA_CACHE[cache_key] = metadata
            logger.info(f"Extracted prompt metadata: {metadata}")
            return metadata
    except (asyncio.TimeoutError, json.JSONDecodeError, Exception) as e:
        logger.warning(f"Metadata extraction failed ({type(e).__name__}), using defaults")

    _METADATA_CACHE[cache_key] = defaults
    return defaults


def _check_command_available(command: str) -> bool:
    """Check if a command is available on the system PATH."""
    import shutil
    return shutil.which(command) is not None


@dataclass
class ExtractedCommand:
    """Result of _extract_terminal_command with full provenance."""
    command: str
    requires_confirmation: bool
    source_path: str  # "hardcoded_safe" | "user_input_quoted" | "user_input_unquoted" | "known_cmd"


_DESTRUCTIVE_CMD_BASENAMES = {
    "format", "diskpart", "taskkill", "shutdown", "restart", "logoff",
    "del", "rmdir", "rd", "rm", "move", "ren", "rename", "cacls",
    "icacls", "takeown", "sfc", "chkdsk", "defrag", "regedit",
    "attrib", "cipher", "compact", "fsutil",
}


def _is_destructive_command_string(cmd: str) -> bool:
    """Classify a command string as destructive (requires user confirmation)."""
    tokens = cmd.strip().split()
    if not tokens:
        return False
    prog = os.path.basename(tokens[0]).lower()
    if prog in _DESTRUCTIVE_CMD_BASENAMES:
        return True
    args = " ".join(tokens[1:]) if len(tokens) > 1 else ""
    if re.search(r'>\s*[A-Z]:\\', args, re.IGNORECASE):
        return True
    if re.search(r'\b(del|rmdir|rm|rd)\s+.*[*?]', args, re.IGNORECASE):
        return True
    return False


_DESTRUCTIVE_PROMPT_PATTERNS = [
    r'\bformat\b.*\b(drive|disk|volume)\b',
    r'\bformat\b.*[cde]:\\',
    r'\bshutdown\b',
    r'\brestart\b',
    r'\bdelete\b.*\b(everything|all|entire)\b',
    r'\bremove\b.*\b(everything|all|entire)\b',
    r'\berase\b.*\b(everything|all|entire)\b',
    r'\bwipe\b.*\b(drive|disk|everything|all)\b',
    r'\brm\s+-rf?\s+[/\\]',
    r'\bdel\s+[/\\][sqr]\b',
]


def _is_destructive_prompt(prompt: str) -> bool:
    """Detect destructive intent from a user prompt (format drive, shutdown, delete everything, etc.)."""
    p = prompt.lower().strip()
    for pattern in _DESTRUCTIVE_PROMPT_PATTERNS:
        if re.search(pattern, p, re.IGNORECASE):
            return True
    return False


def _parse_email_intent(prompt: str) -> Optional[Dict[str, str]]:
    """Extract email intent (to, subject, body) from a user prompt.
    Returns None if no email task is detected. Subject/body may be empty strings."""
    prompt_lower = prompt.lower()
    # Must have an email address AND email-related keywords
    email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', prompt)
    if not email_match:
        return None
    has_send_signal = any(k in prompt_lower for k in ["send", "email", "mail", "message"])
    has_content_signal = any(k in prompt_lower for k in [
        "subject", "body", "saying", "content", "about", "regarding",
        "to ", "compose", "write",
    ])
    if not (has_send_signal and has_content_signal):
        return None

    to_email = email_match.group(0)
    # Subject extraction
    subject = ""
    subj_match = re.search(
        r'(?:subject|about|regarding|re)\s+(.+?)(?:\s+body|\s+saying|\s+content|\s+message|\s+with|\s*$)',
        prompt_lower,
    )
    if subj_match:
        subject = subj_match.group(1).strip().strip('"\'')
    # Body extraction — priority order
    body = ""
    # Pattern 1: body/saying/content/message followed by text
    body_match = re.search(r'(?:body|saying|content|message)\s+["\']?(.+?)["\']?\s*$', prompt)
    if body_match:
        body = body_match.group(1).strip().strip('"\'')
    # Pattern 2: with "text" or with text
    if not body:
        body_match = re.search(r'with\s+["\'](.+?)["\']', prompt)
        if body_match:
            body = body_match.group(1).strip()
    if not body:
        body_match = re.search(r'with\s+(\S+(?:\s+\S+){0,10})', prompt)
        if body_match:
            candidate = body_match.group(1).strip().strip('"\'')
            for kw in ["subject", "to ", "from"]:
                if candidate.lower().startswith(kw):
                    candidate = ""
                    break
            body = candidate
    # Pattern 3: quoted text anywhere in prompt
    if not body:
        body_match = re.search(r'["\'](.+?)["\']', prompt)
        if body_match:
            body = body_match.group(1).strip()
    # Pattern 4: everything after the email address
    if not body:
        after_email = re.split(r'@\S+\s*', prompt, maxsplit=1)
        if len(after_email) > 1:
            candidate = after_email[1].strip().strip('"\'').lstrip('to ').strip()
            for prefix in ["about ", "regarding ", "re ", "subject "]:
                if candidate.lower().startswith(prefix):
                    candidate = candidate[len(prefix):].strip()
                    break
            if candidate and len(candidate) > 3 and not candidate.startswith('subject '):
                body = candidate

    return {"to": to_email, "subject": subject, "body": body}


class PlannerService:
    def __init__(self):
        # Build the LangGraph workflow graph
        workflow = StateGraph(PlannerState)
        
        # Define graph nodes
        workflow.add_node("intent_parser", self._node_parse_intent)
        workflow.add_node("plan_generator", self._node_generate_plan)
        workflow.add_node("plan_validator", self._node_validate_plan)
        
        # Setup paths/edges
        workflow.set_entry_point("intent_parser")
        workflow.add_edge("intent_parser", "plan_generator")
        workflow.add_edge("plan_generator", "plan_validator")
        workflow.add_edge("plan_validator", END)
        
        self.app = workflow.compile()

    async def generate_workflow_steps(self, prompt: str) -> Dict[str, Any]:
        """LLM-first planning. Falls back to rule-based only when LLM fails or returns empty."""
        prompt_lower = prompt.lower()

        # PRIMARY: Send to LLM planner — it understands natural language best
        llm_steps = []
        try:
            initial_state = PlannerState(user_prompt=prompt)
            final_state = await self.app.ainvoke(initial_state)

            if final_state.get("errors"):
                logger.warning(f"LLM planner errors: {final_state['errors']}")

            llm_steps = final_state.get("steps", [])
            # Normalize LLM output: fix common field name mistakes
            for idx, step in enumerate(llm_steps):
                if "parameters" not in step and "params" in step:
                    step["parameters"] = step.pop("params")
                if "step_id" not in step:
                    step["step_id"] = f"step_{idx + 1}"
                if "name" not in step:
                    step["name"] = step.get("action", "unknown")
        except Exception as e:
            logger.warning(f"LLM planner failed: {e}. Falling back to rule-based.")

        if llm_steps:
            # The 7B model often returns only 1 step — complete the plan if incomplete
            llm_steps = await self._complete_incomplete_plan(prompt, llm_steps)
            logger.info(f"Using LLM plan for prompt: {prompt[:80]} ({len(llm_steps)} steps)")

            # Sanity check: parsed_intent vs actual step agent types
            parsed_intent = final_state.get("parsed_intent", "")
            intent_agent_map = {
                "shell_execution": "terminal",
                "browser_search": "browser",
                "file_system_operations": "file",
                "desktop_macro": "desktop",
            }
            expected_agent = intent_agent_map.get(parsed_intent)
            if expected_agent:
                actual_agents = {s.get("agent_type") for s in llm_steps}
                if expected_agent not in actual_agents and actual_agents:
                    logger.warning(
                        f"Intent-step mismatch: parsed_intent={parsed_intent} expects {expected_agent} "
                        f"but steps use {actual_agents}. Prompt: {prompt[:80]}"
                    )

            result = {"steps": llm_steps}

            # Surface inline pending_confirmation from steps (e.g. Fix 1b destructive terminal commands)
            for s in llm_steps:
                if "pending_confirmation" in s:
                    result["pending_confirmation"] = s.pop("pending_confirmation")
                    break

            # Detect email task from the PROMPT itself — always force confirmation
            email_intent = _parse_email_intent(prompt)
            if email_intent:
                to_email = email_intent["to"]
                subject = email_intent["subject"]
                body = email_intent["body"]
                # Generate body via LLM — do it when body is empty OR same as subject
                if not body or body.strip().lower() == subject.strip().lower():
                    try:
                        generated = await asyncio.wait_for(
                            llm_service.generate(
                                prompt=f"Write a short professional email body about: {subject or prompt}. Do NOT use placeholders. Write real content.",
                                temperature=0.5,
                                max_tokens=300,
                            ),
                            timeout=30.0,
                        )
                        if generated:
                            body = generated.strip()
                    except Exception:
                        body = subject or prompt
                if not body:
                    body = subject or prompt

                # Email confirmation — extract details from prompt (safety: always confirm before sending)
                logger.info(f"Email task detected — forcing confirmation for: {to_email}")
                result["pending_confirmation"] = {
                    "type": "email_draft",
                    "to": to_email,
                    "subject": subject,
                    "body": body,
                }

            # Detect destructive intent from prompt — always force confirmation
            if "pending_confirmation" not in result and _is_destructive_prompt(prompt):
                destructive_cmd = prompt.strip()
                cmd_extract = self._extract_terminal_command(prompt)
                if cmd_extract:
                    destructive_cmd = cmd_extract.command
                result["pending_confirmation"] = {
                    "type": "terminal_command",
                    "command": destructive_cmd,
                    "message": f"The command '{destructive_cmd}' requires your confirmation before execution.",
                    "source": "destructive_prompt_detection",
                }
                logger.info(f"Destructive prompt detected — forcing confirmation: {prompt[:80]}")

            # Detect file write steps — always force confirmation
            if "pending_confirmation" not in result:
                for s in llm_steps:
                    if s.get("agent_type") == "file" and s.get("action") in ("write", "create"):
                        file_path = s.get("parameters", {}).get("path", s.get("parameters", {}).get("filename", "unknown"))
                        result["pending_confirmation"] = {
                            "type": "file_write",
                            "path": file_path,
                            "message": f"ACO wants to create file at {file_path}. Allow?",
                        }
                        logger.info(f"File write detected — forcing confirmation: {file_path}")
                        break

            return result

        # FALLBACK: Rule-based for simple, unambiguous patterns (when LLM fails)
        logger.info(f"LLM returned no steps, trying rule-based fallback for: {prompt[:80]}")
        rule_result = await self._generate_rule_based_fallback(prompt)
        rule_steps = rule_result.get("steps", [])
        if rule_steps:
            logger.info(f"Using rule-based plan for prompt: {prompt[:80]}")
            result = rule_result  # already contains "steps" + optional "pending_confirmation"
            to_email = ""
            subject = ""
            body = ""
            for s in rule_steps:
                if s.get("action") == "fill" and "recipient" in s.get("name", "").lower():
                    to_email = s.get("parameters", {}).get("value", "")
                if s.get("action") == "fill" and "subject" in s.get("name", "").lower():
                    subject = s.get("parameters", {}).get("value", "")
                if s.get("action") == "fill" and "body" in s.get("name", "").lower():
                    body = s.get("parameters", {}).get("value", "")
            if to_email and subject:
                result["pending_confirmation"] = {
                    "type": "email_draft",
                    "to": to_email,
                    "subject": subject,
                    "body": body,
                }
            return result

        # Both failed — return empty
        raise ValueError(f"Could not generate a plan for: {prompt}")

    async def _node_parse_intent(self, state: PlannerState) -> Dict[str, Any]:
        """Resolves raw user prompt into high-level categorization."""
        prompt = state.user_prompt.lower()
        intent = "general_automation"

        if any(k in prompt for k in ["browser", "website", "google", "http", "navigate", "url",
                                      "email", "gmail", "mail", "inbox", "message", "summarize",
                                      "sumarize", "youtube", "open chrome", "open browser"]):
            intent = "browser_search"
        elif any(k in prompt for k in ["click", "type", "screen", "mouse", "keyboard", "drag"]):
            intent = "desktop_macro"
        elif any(k in prompt for k in ["spreadsheet", "excel", "csv", "file", "folder", "delete",
                                       "read file", "write file", "document", "pdf"]):
            intent = "file_system_operations"
        elif any(k in prompt for k in ["cmd", "terminal", "run", "ping", "shell", "powershell",
                                       "command", "execute", "bash", "script"]):
            intent = "shell_execution"

        return {"parsed_intent": intent}

    async def _node_generate_plan(self, state: PlannerState) -> Dict[str, Any]:
        """Queries local Ollama (Qwen 3) to generate a structured JSON execution plan."""

        system_instruction = (
            "You are an AI task planner. Given a user request, output a JSON array of steps.\n"
            "\n"
            "AGENTS: browser (navigate, click, fill, press, wait, wait_for_selector, scrape_text, scrape_links, summarize), "
            "terminal (run), file (read, write, list, delete, find_text, search), desktop (click, type, press)\n"
            "\n"
            "CRITICAL RULES:\n"
            "1. ALWAYS return a JSON ARRAY of multiple steps. NEVER return a single object. NEVER return just navigate.\n"
            "2. Every task that opens a website MUST include follow-up actions (scrape, fill, click, etc.)\n"
            "3. Every step: {step_id, name, agent_type, action, parameters}\n"
            "4. Windows: dir not ls, ping -n not -c\n"
            "\n"
            "EXAMPLE - 'summarize the last 5 emails':\n"
            '[{"step_id":"step_1","name":"Open Gmail inbox","agent_type":"browser","action":"navigate","parameters":{"url":"https://mail.google.com/mail/u/0/#inbox"}},'
            '{"step_id":"step_2","name":"Extract email list","agent_type":"browser","action":"scrape_text","parameters":{}},'
            '{"step_id":"step_3","name":"Summarize emails","agent_type":"browser","action":"summarize","parameters":{"query":"Summarize the last 5 emails"}}]\n'
            "\n"
            "EXAMPLE - 'send email to x@y.com about meeting':\n"
            '[{"step_id":"step_1","name":"Open Gmail compose","agent_type":"browser","action":"navigate","parameters":{"url":"https://mail.google.com/mail/u/0/#inbox?compose=new"}},'
            '{"step_id":"step_2","name":"Wait for compose","agent_type":"browser","action":"wait_for_selector","parameters":{"selector":"input[aria-label=\'To recipients\']","timeout":15}},'
            '{"step_id":"step_3","name":"Fill recipient","agent_type":"browser","action":"fill","parameters":{"selector":"input[aria-label=\'To recipients\']","value":"x@y.com"}},'
            '{"step_id":"step_4","name":"Tab to confirm","agent_type":"browser","action":"press","parameters":{"key":"Tab"}},'
            '{"step_id":"step_5","name":"Fill subject","agent_type":"browser","action":"fill","parameters":{"selector":"input[name=\'subjectbox\']","value":"Meeting"}},'
            '{"step_id":"step_6","name":"Fill body","agent_type":"browser","action":"fill","parameters":{"selector":"div[role=\'textbox\'][aria-label=\'Message Body\']","value":"Hi, about the meeting."}},'
            '{"step_id":"step_7","name":"Send","agent_type":"browser","action":"click","parameters":{"selector":"div[role=\'button\'][aria-label*=\'Send\']"}}]\n'
            "\n"
            "EXAMPLE - 'search google for machine learning':\n"
            '[{"step_id":"step_1","name":"Open Google","agent_type":"browser","action":"navigate","parameters":{"url":"https://www.google.com"}},'
            '{"step_id":"step_2","name":"Type search","agent_type":"browser","action":"fill","parameters":{"selector":"input[name=\'q\']","value":"machine learning"}},'
            '{"step_id":"step_3","name":"Submit","agent_type":"browser","action":"press","parameters":{"key":"Enter"}},'
            '{"step_id":"step_4","name":"Extract results","agent_type":"browser","action":"scrape_text","parameters":{}}]\n'
            "\n"
            "OUTPUT: ONLY a JSON array. No markdown. No text. Just the array.\n"
        )

        prompt_payload = (
            f"User request: '{state.user_prompt}'\n"
            f"Detected intent: {state.parsed_intent}\n"
            "Generate a complete multi-step plan. Return ONLY the JSON array."
        )

        steps = []
        errors = []

        try:
            content = await llm_service.generate(
                prompt=prompt_payload,
                system=system_instruction,
                response_format="json",
                temperature=0.0,
                max_tokens=4096,
            )
            logger.debug(f"Planner LLM output text: {content}")
            logger.info(f"Planner LLM raw output ({len(content)} chars): {content[:500]}")

            # Attempt to extract JSON array from the response
            raw_text = content.strip()
            try:
                if "```" in raw_text:
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                parsed = json.loads(raw_text.strip())
                # Handle multiple response formats the LLM might return
                if isinstance(parsed, dict):
                    # LLM might wrap steps in a dict: {"steps": [...]} or {"plan": [...]}
                    if "steps" in parsed and isinstance(parsed["steps"], list):
                        steps = parsed["steps"]
                    elif "plan" in parsed and isinstance(parsed["plan"], list):
                        steps = parsed["plan"]
                    else:
                        steps = [parsed]
                elif isinstance(parsed, list):
                    steps = parsed
                else:
                    errors.append(f"Unexpected JSON type: {type(parsed).__name__}. Raw: {content}")
            except json.JSONDecodeError as je:
                errors.append(f"Failed to parse LLM JSON output: {je}. Raw output was: {content}")
                steps = await self._generate_rule_based_fallback(state.user_prompt)
                steps = steps.get("steps", []) if isinstance(steps, dict) else steps
                logger.info(f"Falling back to rule-based planner after JSON parse failure")
            if not steps:
                fallback = await self._generate_rule_based_fallback(state.user_prompt)
                steps = fallback.get("steps", []) if isinstance(fallback, dict) else fallback

        except Exception as e:
            logger.warning(f"LLM execution failed: {e}. Falling back to rule-based parser.")
            fallback = await self._generate_rule_based_fallback(state.user_prompt)
            steps = fallback.get("steps", []) if isinstance(fallback, dict) else fallback

        logger.info(f"Planner final plan: {len(steps)} steps")
        return {"steps": steps, "errors": errors}

    async def _node_validate_plan(self, state: PlannerState) -> Dict[str, Any]:
        """Validates that agent types and parameter schemas match constraints."""
        from app.ai.capabilities import capability_registry

        valid_agents = set(capability_registry.all_agents().keys())
        allowed_actions = {
            agent: caps.actions
            for agent, caps in capability_registry.all_agents().items()
        }
        errors = []
        
        for idx, step in enumerate(state.steps):
            agent = step.get("agent_type")
            action = step.get("action")
            step_id = step.get("step_id", f"step_{idx}")

            if agent not in valid_agents:
                errors.append(f"[{step_id}] Invalid agent type specified: {agent}")
            if not action:
                errors.append(f"[{step_id}] Missing action instruction.")
                continue
            if agent in allowed_actions and action not in allowed_actions[agent]:
                errors.append(f"[{step_id}] Action '{action}' not allowed for agent '{agent}'. Allowed: {', '.join(sorted(allowed_actions[agent]))}")

        is_valid = len(errors) == 0
        return {"errors": state.errors + errors, "is_valid": is_valid}

    async def _complete_incomplete_plan(self, prompt: str, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """When the 7B model returns only 1 step, complete the plan based on intent."""
        if len(steps) > 1:
            return steps

        step = steps[0]
        prompt_lower = prompt.lower()
        max_idx = 1

        def _next():
            nonlocal max_idx
            max_idx += 1
            return f"step_{max_idx}"

        # Extract metadata once for all child methods
        metadata = await _extract_prompt_metadata(prompt)

        # --- Terminal / Code tasks: single terminal step with empty or incomplete command ---
        if step.get("agent_type") == "terminal" and step.get("action") == "run":
            params = step.get("parameters", {})
            cmd = params.get("command", "").strip()
            _placeholder_cmds = ("code", "cmd", "powershell", "terminal", "bash", "cmd.exe", "open terminal", "open cmd", "open powershell")
            if not cmd or cmd.lower() in _placeholder_cmds:
                # LLM returned a placeholder — ask LLM to generate the actual command
                try:
                    generated_cmd = await asyncio.wait_for(
                        llm_service.generate(
                            prompt=(
                                f"Given this user request: \"{prompt}\"\n"
                                f"Generate the exact PowerShell command to accomplish it.\n"
                                f"Return ONLY the raw command, nothing else. No explanation, no markdown, no quotes."
                            ),
                            temperature=0.0,
                            max_tokens=200,
                        ),
                        timeout=15.0,
                    )
                    if generated_cmd:
                        real_cmd = generated_cmd.strip().strip('`"\'')
                        if real_cmd and real_cmd.lower() not in _placeholder_cmds:
                            step["name"] = f"Run: {real_cmd}"
                            step["parameters"] = {"command": real_cmd}
                            if _is_destructive_command_string(real_cmd):
                                step["pending_confirmation"] = {
                                    "type": "terminal_command",
                                    "command": real_cmd,
                                    "message": f"The command '{real_cmd}' requires your confirmation before execution.",
                                    "source": "llm_generated",
                                }
                            return [step]
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"LLM command generation failed: {e}")

        # --- File tasks: single file step with incomplete action ---
        if step.get("agent_type") == "file" and step.get("action") == "create":
            params = step.get("parameters", {})
            content = params.get("content", "").strip()
            if not content or content.startswith("{"):
                follow_ups = await self._complete_file_plan(prompt, prompt_lower, step, _next, metadata)
                if follow_ups:
                    return steps + follow_ups

        # --- Desktop steps: LLM tried to open IDE instead of generating code ---
        if step.get("agent_type") == "desktop" and re.search(r'(?:create|write|make|build|code|program|script)', prompt_lower):
            follow_ups = await self._complete_terminal_plan(prompt, prompt_lower, step, _next, metadata)
            if follow_ups:
                return steps + follow_ups
            # If command exists but is just "code" or similar, also try to complete
            if cmd and cmd.lower() in ("code", "cmd", "powershell", "terminal", "bash", "cmd.exe"):
                follow_ups = await self._complete_terminal_plan(prompt, prompt_lower, step, _next)
                if follow_ups:
                    return steps + follow_ups

        # --- File tasks: single file step with incomplete action ---
        if step.get("agent_type") == "file" and step.get("action") == "create":
            params = step.get("parameters", {})
            content = params.get("content", "").strip()
            if not content or content.startswith("{"):
                # LLM returned file create but forgot the content
                follow_ups = await self._complete_file_plan(prompt, prompt_lower, step, _next)
                if follow_ups:
                    return steps + follow_ups

        # --- Desktop steps: LLM tried to open IDE instead of generating code ---
        if step.get("agent_type") == "desktop" and re.search(r'(?:create|write|make|build|code|program|script)', prompt_lower):
            follow_ups = await self._complete_terminal_plan(prompt, prompt_lower, step, _next)
            if follow_ups:
                return steps + follow_ups

        # --- Desktop steps: LLM returned desktop click but user wants file/search/list operations ---
        if step.get("agent_type") == "desktop":
            # Detect file search/list/find intent
            is_file_search = any(k in prompt_lower for k in [
                "find", "search", "list", "show", "get", "locate",
                "all pdf", "all doc", "all txt", "all jpg", "all png",
                "all mp3", "all mp4", "all zip", "all py", "all js",
                "files", "documents", "photos", "images", "videos",
            ])
            is_directory_list = any(k in prompt_lower for k in [
                "what's in", "what is in", "folder", "directory", "contents",
                "on my desktop", "in my desktop", "on desktop", "in desktop",
                "on my documents", "in my documents", "on my downloads",
            ])
            if is_file_search or is_directory_list:
                # Convert desktop click to proper file list step
                target_path = None
                for keyword in ["desktop", "documents", "downloads", "pictures", "music", "videos"]:
                    if keyword in prompt_lower:
                        target_path = get_user_dir(keyword)
                        break
                if not target_path:
                    target_path = get_user_dir("desktop")

                # Detect file extension from prompt
                ext = None
                ext_match = re.search(r'\.(\w{1,5})\b', prompt_lower)
                if ext_match:
                    ext = ext_match.group(1)
                else:
                    # Try to extract extension from patterns like "pdf files", "doc files"
                    ext_word_match = re.search(r'(?:all\s+)?(\w+)\s*(?:files?|docs?|documents?)', prompt_lower)
                    if ext_word_match:
                        candidate = ext_word_match.group(1)
                        known_exts = {"pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "gif",
                                       "mp3", "mp4", "avi", "mkv", "wav", "zip", "rar",
                                       "py", "js", "ts", "java", "cpp", "c", "rs", "go", "html", "css", "json"}
                        if candidate in known_exts:
                            ext = candidate

                step["name"] = f"List files in {target_path}" + (f" (*.{ext})" if ext else "")
                step["agent_type"] = "file"
                step["action"] = "list"
                params = {"path": target_path}
                if ext:
                    params["extension"] = ext
                step["parameters"] = params
                logger.info(f"Converted desktop step to file/list: {step['name']}")
                return [step]

        # --- Desktop steps: catch-all for any remaining desktop steps with no useful params ---
        if step.get("agent_type") == "desktop":
            action = step.get("action", "")
            params = step.get("parameters", {})
            needs_params = (
                (action == "click" and ("x" not in params or "y" not in params))
                or (action == "type" and "text" not in params)
                or (action == "press" and "key" not in params)
            )
            if needs_params:
                # LLM returned wrong agent type — use LLM to generate the actual command
                try:
                    generated_cmd = await asyncio.wait_for(
                        llm_service.generate(
                            prompt=(
                                f"Given this user request: \"{prompt}\"\n"
                                f"Generate the exact PowerShell command to accomplish it.\n"
                                f"Return ONLY the raw command, nothing else. No explanation, no markdown, no quotes."
                            ),
                            temperature=0.0,
                            max_tokens=200,
                        ),
                        timeout=15.0,
                    )
                    if generated_cmd:
                        real_cmd = generated_cmd.strip().strip('`"\'')
                        step["agent_type"] = "terminal"
                        step["action"] = "run"
                        step["name"] = f"Run: {real_cmd}"
                        step["parameters"] = {"command": real_cmd}
                        if _is_destructive_command_string(real_cmd):
                            step["pending_confirmation"] = {
                                "type": "terminal_command",
                                "command": real_cmd,
                                "message": f"The command '{real_cmd}' requires your confirmation before execution.",
                                "source": "llm_generated",
                            }
                        return [step]
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"LLM command generation for desktop fallback failed: {e}")
                # Fallback: echo
                step["agent_type"] = "terminal"
                step["action"] = "run"
                step["parameters"] = {"command": f'echo "ACO: could not determine command for: {prompt[:80]}"'}
                step["name"] = f"Skipped: desktop/{action} (missing params)"
                return [step]

        if step.get("action") != "navigate" or step.get("agent_type") != "browser":
            return steps

        url = step.get("parameters", {}).get("url", "")

        follow_ups = []

        # --- Gmail / Email patterns ---
        if "gmail" in url or "mail.google.com" in url:
            if any(k in prompt_lower for k in ["summarize", "summary", "read", "last", "recent", "emails", "inbox"]):
                follow_ups = [
                    {"step_id": _next(), "name": "Extract email list", "agent_type": "browser", "action": "scrape_text", "parameters": {}},
                    {"step_id": _next(), "name": "Summarize emails", "agent_type": "browser", "action": "summarize", "parameters": {"query": f"Summarize the content. {prompt}"}},
                ]
            elif any(k in prompt_lower for k in ["compose", "send", "email to", "mail to", "write"]):
                email_intent = _parse_email_intent(prompt)
                to_email = email_intent["to"] if email_intent else ""
                subject = email_intent["subject"] if email_intent else ""
                # Override URL: Gmail compose URL fails after auth redirect, go to inbox and click compose
                step["parameters"]["url"] = "https://mail.google.com/mail/u/0/#inbox"
                step["name"] = "Open Gmail inbox"
                follow_ups = [
                    {"step_id": _next(), "name": "Wait for inbox to load", "agent_type": "browser", "action": "wait_for_selector", "parameters": {"selector": "div[role='main']", "timeout": 20}},
                    {"step_id": _next(), "name": "Click Compose button", "agent_type": "browser", "action": "click", "parameters": {"selector": "div[role='button'][aria-label='Compose']", "fallback_text": "Compose"}},
                    {"step_id": _next(), "name": "Wait for compose window", "agent_type": "browser", "action": "wait_for_selector", "parameters": {"selector": "input[aria-label='To recipients']", "timeout": 15}},
                    {"step_id": _next(), "name": "Fill recipient", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[aria-label='To recipients']", "value": to_email}},
                    {"step_id": _next(), "name": "Tab to confirm", "agent_type": "browser", "action": "press", "parameters": {"key": "Tab"}},
                ]
                if subject:
                    follow_ups.append({"step_id": _next(), "name": "Fill subject", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[name='subjectbox']", "value": subject.title()}})
                follow_ups.extend([
                    {"step_id": _next(), "name": "Fill body", "agent_type": "browser", "action": "fill", "parameters": {"selector": "div[role='textbox'][aria-label='Message Body']", "value": f"Hi, this regards: {subject}."}},
                    {"step_id": _next(), "name": "Wait before sending", "agent_type": "browser", "action": "wait", "parameters": {"seconds": 3}},
                    {"step_id": _next(), "name": "Click Send", "agent_type": "browser", "action": "click", "parameters": {"selector": "div[role='button'][aria-label*='Send']"}},
                ])
            else:
                follow_ups = [
                    {"step_id": _next(), "name": "Extract page content", "agent_type": "browser", "action": "scrape_text", "parameters": {}},
                ]

        # --- Google search ---
        elif "google.com" in url and "mail" not in url:
            query = ""
            q_match = re.search(r'for\s+(.+?)(?:\s*$)', prompt_lower)
            if q_match:
                query = q_match.group(1).strip()
            elif "?" in prompt:
                query = prompt.split("?")[0].strip()
            else:
                query = prompt
            follow_ups = [
                {"step_id": _next(), "name": "Type search query", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[name='q']", "value": query}},
                {"step_id": _next(), "name": "Submit search", "agent_type": "browser", "action": "press", "parameters": {"key": "Enter"}},
                {"step_id": _next(), "name": "Extract search results", "agent_type": "browser", "action": "scrape_text", "parameters": {}},
            ]
            if any(k in prompt_lower for k in ["summarize", "summary", "explain"]):
                follow_ups.append({"step_id": _next(), "name": "Summarize results", "agent_type": "browser", "action": "summarize", "parameters": {"query": prompt}})

        # --- YouTube ---
        elif "youtube" in url:
            query = ""
            q_match = re.search(r'(?:search|for)\s+(.+?)(?:\s*$)', prompt_lower)
            if q_match:
                query = q_match.group(1).strip()
            else:
                query = prompt
            follow_ups = [
                {"step_id": _next(), "name": "Type search query", "agent_type": "browser", "action": "fill", "parameters": {"selector": "input[name='search_query']", "value": query}},
                {"step_id": _next(), "name": "Submit search", "agent_type": "browser", "action": "press", "parameters": {"key": "Enter"}},
                {"step_id": _next(), "name": "Wait for results", "agent_type": "browser", "action": "wait", "parameters": {"seconds": 3}},
                {"step_id": _next(), "name": "Extract video links", "agent_type": "browser", "action": "scrape_links", "parameters": {"domain_filter": "youtube.com/watch"}},
            ]
            if any(k in prompt_lower for k in ["summarize", "summary"]):
                follow_ups.append({"step_id": _next(), "name": "Summarize videos", "agent_type": "browser", "action": "summarize", "parameters": {"query": prompt}})

        # --- Generic website ---
        else:
            follow_ups = [
                {"step_id": _next(), "name": "Extract page content", "agent_type": "browser", "action": "scrape_text", "parameters": {}},
            ]
            if any(k in prompt_lower for k in ["summarize", "summary"]):
                follow_ups.append({"step_id": _next(), "name": "Summarize page", "agent_type": "browser", "action": "summarize", "parameters": {"query": prompt}})

        if follow_ups:
            logger.info(f"Completed plan: {len(steps)} -> {len(steps) + len(follow_ups)} steps (added {len(follow_ups)} follow-up steps)")
            return steps + follow_ups
        return steps

    async def _complete_terminal_plan(self, prompt: str, prompt_lower: str, first_step: Dict, _next,
                                      metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate a multi-step plan for terminal/code tasks when LLM returns only a bare terminal step."""
        home = os.path.expanduser("~")
        default_output = os.path.join(home, "ACO_Output")
        follow_ups = []
        meta = metadata or {}

        # --- Code creation: "create/write/make a program in C/Python/etc." ---
        code_match = re.search(
            r'(?:create|write|make|build|code)\s+(?:a\s+)?(.+?)(?:\s+program|\s+script|\s+file|\s+code|\s+in\b|\s+that\b|\s+to\b|\s*$)',
            prompt_lower
        )

        if code_match or re.search(r'(?:create|write|make|build|code)', prompt_lower):
            # Detect language via centralized detector (use metadata if available)
            lang_def = LanguageDetector.detect(prompt)
            if meta.get("language"):
                detected = _NAME_TO_DEF.get(meta["language"].lower())
                if detected:
                    lang_def = detected

            # Resolve target directory from metadata
            target_dir = default_output
            if meta.get("target_directory"):
                target_dir = get_user_dir(meta["target_directory"])

            # Build filename from metadata or fallback to topic
            if meta.get("filename"):
                fname = meta["filename"]
                _, has_ext = os.path.splitext(fname)
                if has_ext:
                    filename = fname  # Already has extension, use directly
                else:
                    filename = ExecutionDispatcher.build_filename(fname, lang_def)
            elif meta.get("topic"):
                filename = ExecutionDispatcher.build_filename(meta["topic"], lang_def)
            else:
                # Fallback: strip common words + location keywords
                topic = re.sub(r'\b(?:create|write|make|build|code|a|an|the|program|script|file|in|using|with|that|to|for|on|my|at|from)\b\s*', '', prompt_lower).strip()
                topic = re.sub(r'[^a-z0-9_]+', '_', topic).strip('_')[:40] or "program"
                filename = ExecutionDispatcher.build_filename(topic, lang_def)

            filepath = os.path.join(target_dir, filename)

            # Generate code via LLM
            code = await self._generate_code(prompt, lang_def.name)
            if not code:
                logger.warning(f"LLM code generation failed for {lang_def.name}, using stub")
                code = self._stub_code(prompt, meta.get("topic") or filename, lang_def)

            # Ensure output directory exists
            os.makedirs(target_dir, exist_ok=True)

            # Update the first step to write the file using the file agent
            first_step["name"] = f"Write {filename}"
            first_step["agent_type"] = "file"
            first_step["action"] = "write"
            first_step["parameters"] = {"path": filepath, "content": code}

            # Compile step (if needed)
            compile_info = ExecutionDispatcher.compile_command(filepath, lang_def, target_dir)
            if compile_info:
                compiler_bin, compile_cmd = compile_info
                ok, msg = CompilerManager.check_language(lang_def)
                if ok:
                    follow_ups.append({"step_id": _next(), "name": f"Compile {filename}", "agent_type": "terminal", "action": "run",
                                      "parameters": {"command": compile_cmd}})
                else:
                    logger.warning(msg)
                    follow_ups.append({"step_id": _next(), "name": f"Compiler not found ({compiler_bin})", "agent_type": "terminal", "action": "run",
                                      "parameters": {"command": f'echo "WARNING: {msg}"'}})

            # Run step
            run_cmd = ExecutionDispatcher.run_command(filepath, lang_def, target_dir)
            follow_ups.append({"step_id": _next(), "name": f"Run {filename}", "agent_type": "terminal", "action": "run",
                              "parameters": {"command": run_cmd}})

            logger.info(f"Completed terminal/code plan: {len(follow_ups)} steps for {lang_def.name} program")
            return follow_ups

        # --- Generic terminal: "run X in terminal" where command is missing ---
        cmd_match = re.search(r'(?:run|execute|command|enter)\s+(.+?)(?:\s+in\s+(?:the\s+)?terminal|\s+and\s+show|\s*$)', prompt_lower)
        if cmd_match:
            cmd = cmd_match.group(1).strip()
            first_step["name"] = f"Run: {cmd}"
            first_step["parameters"] = {"command": cmd}
            if _is_destructive_command_string(cmd):
                first_step["pending_confirmation"] = {
                    "type": "terminal_command",
                    "command": cmd,
                    "message": f"The command '{cmd}' requires your confirmation before execution.",
                    "source": "user_input_unquoted",
                }
            return []

        return []

    @staticmethod
    def _stub_code(prompt: str, topic: str, lang_def: LanguageDef) -> str:
        """Generate a minimal stub when LLM code generation fails."""
        safe_topic = topic.replace('"', '\\"')
        stubs = {
            "python": f'"""TODO: Implement - {prompt}"""\n\ndef main():\n    print("TODO: Implement {safe_topic}")\n\nif __name__ == "__main__":\n    main()\n',
            "cpp": (
                f"#include <iostream>\n\n"
                f"// TODO: Implement - {prompt}\n"
                f"int main() {{\n"
                f'    std::cout << "TODO: Implement {safe_topic}" << std::endl;\n'
                f"    return 0;\n}}\n"
            ),
            "c": (
                f"#include <stdio.h>\n\n"
                f"// TODO: Implement - {prompt}\n"
                f"int main() {{\n"
                f'    printf("TODO: Implement {safe_topic}\\n");\n'
                f"    return 0;\n}}\n"
            ),
            "java": f"public class {topic} {{\n    public static void main(String[] args) {{\n        System.out.println(\"TODO: Implement {safe_topic}\");\n    }}\n}}\n",
            "javascript": f"// TODO: Implement - {prompt}\nconsole.log('TODO: Implement {safe_topic}');\n",
            "go": f'package main\n\nimport "fmt"\n\n// TODO: Implement - {prompt}\nfunc main() {{\n    fmt.Println("TODO: Implement {safe_topic}")\n}}\n',
            "rust": f'// TODO: Implement - {prompt}\nfn main() {{\n    println!("TODO: Implement {safe_topic}");\n}}\n',
            "php": f"<?php\n// TODO: Implement - {prompt}\necho 'TODO: Implement {safe_topic}' . PHP_EOL;\n",
            "ruby": f"# TODO: Implement - {prompt}\nputs 'TODO: Implement {safe_topic}'\n",
            "html": f"<!DOCTYPE html>\n<html><head><title>{safe_topic}</title></head><body><h1>TODO: Implement</h1><p>{prompt}</p></body></html>\n",
            "css": f"/* TODO: Implement - {prompt} */\nbody {{ margin: 0; padding: 0; }}\n",
            "bash": f'#!/bin/bash\n# TODO: Implement - {prompt}\necho "TODO: Implement {safe_topic}"\n',
        }
        return stubs.get(lang_def.name, f"# TODO: Implement - {prompt}\n")

    async def _generate_code(self, prompt: str, lang: str) -> str:
        """Use the LLM to generate code. Retries up to 2 times on failure, 45s timeout each."""
        clean_prompt = (
            f"Write complete, runnable {lang.upper()} code for this request: {prompt}\n"
            f"Output ONLY the code. No explanation, no markdown, no code fences. Just the raw code."
        )
        for attempt in range(2):
            try:
                logger.info(f"Code generation attempt {attempt+1}/2 for {lang}")
                code = await asyncio.wait_for(
                    llm_service.generate(
                        prompt=clean_prompt,
                        temperature=0.2,
                        max_tokens=2000,
                    ),
                    timeout=45.0,
                )
                if code:
                    code = code.strip()
                    if code.startswith("```"):
                        code = code.split("\n", 1)[-1] if "\n" in code else code[3:]
                    if code.endswith("```"):
                        code = code[:-3]
                    code = code.strip()
                    if len(code) > 20:
                        logger.info(f"Code generation succeeded on attempt {attempt+1} ({len(code)} chars)")
                        return code
                    logger.warning(f"Code generation attempt {attempt+1}: too short ({len(code)} chars), retrying")
            except asyncio.TimeoutError:
                logger.warning(f"Code generation attempt {attempt+1} timed out after 45s")
            except Exception as e:
                logger.warning(f"Code generation attempt {attempt+1} failed: {e}")
            if attempt < 1:
                await asyncio.sleep(1)
        logger.error(f"Code generation failed after 2 attempts for {lang}")
        return ""

    async def _complete_file_plan(self, prompt: str, prompt_lower: str, first_step: Dict, _next,
                                  metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Complete a file creation plan when LLM forgot the content or used wrong action."""
        home = os.path.expanduser("~")
        default_output = os.path.join(home, "ACO_Output")
        meta = metadata or {}

        # Resolve target directory from metadata
        target_dir = default_output
        if meta.get("target_directory"):
            target_dir = get_user_dir(meta["target_directory"])
        os.makedirs(target_dir, exist_ok=True)

        # Extract filename from step, metadata, or prompt
        filename = first_step.get("parameters", {}).get("filename", "")
        target_path = first_step.get("parameters", {}).get("path", "")
        if not filename and not target_path:
            if meta.get("filename"):
                filename = meta["filename"]
            else:
                # Fallback: regex extraction
                file_match = re.search(r'(?:named?|called?|as)\s+["\']?(\S+\.\w+)["\']?', prompt_lower)
                if file_match:
                    filename = file_match.group(1)
                else:
                    base_match = re.search(r'(?:file|script)\s+(?:for|with|called|named)\s+(\w+)', prompt_lower)
                    base_name = base_match.group(1) if base_match else "output"
                    lang_def = LanguageDetector.detect(prompt)
                    ext = lang_def.extension
                    ts = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base_name}_{ts}{ext}"

        if not target_path:
            target_path = os.path.join(target_dir, filename)

        # Determine if this is a code request
        code_keywords = ["code", "function", "script", "program", "algorithm", "class",
                        "factorial", "fibonacci", "sort", "calculator", "converter",
                        "flask", "django", "fastapi", "game", "hello world", "print"]
        is_code = (
            any(k in prompt_lower for k in code_keywords)
            or bool(re.search(r'\b(?:python|javascript|typescript|java|c\+\+|ruby|go|rust|php|html|css|sql|bash|shell)\b', prompt_lower))
            or bool(re.search(r'\.\w{1,4}\b', prompt_lower))
        )

        content = None
        if is_code:
            lang_def = LanguageDetector.detect(prompt)
            content = await self._generate_code(prompt, lang_def.name)

        if not content:
            # Non-code file: extract content from prompt, or use default
            content_match = re.search(r'(?:with content|containing|saying|that says|that contains)\s+["\']?(.+?)["\']?\s*$', prompt)
            if content_match:
                content = content_match.group(1)
            else:
                content = f"Created by ACO Agent\nPrompt: {prompt}"

        first_step["name"] = f"Write {filename}"
        first_step["agent_type"] = "file"
        first_step["action"] = "write"
        first_step["parameters"] = {"path": target_path, "content": content}
        logger.info(f"Completed file plan: {filename} ({len(content)} chars)")
        return []

    def _fix_misplaced_desktop_steps(self, prompt: str, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fix LLM mistakes: replace desktop steps with terminal for non-GUI queries."""
        prompt_lower = prompt.lower()
        # Patterns where the user wants info (path, dir listing, system info) — NOT GUI interaction
        info_query_patterns = [
            r'(?:give|show|what|print|get|tell|find|list|display).*(?:path|directory|location|folder)',
            r'(?:desktop|documents?|downloads?|home|user).*(?:path|directory|location)',
            r'(?:my |the ).*(?:current )?(?:directory|folder|path)',
            r'(?:disk|space|memory|cpu|process|system|ipconfig|hostname)',
        ]
        is_info_query = any(re.search(p, prompt_lower) for p in info_query_patterns)
        # Patterns where the user explicitly asks for GUI/click/type/press action
        is_gui_request = any(k in prompt_lower for k in ["click", "type on screen", "press key", "mouse", "keyboard shortcut"])

        if not is_info_query or is_gui_request:
            return steps

        fixed = []
        for step in steps:
            if step.get("agent_type") == "desktop":
                action = step.get("action", "")
                params = step.get("parameters", {})
                # Replace desktop press/type with terminal equivalents
                if action == "press":
                    key = params.get("key", "")
                    # Win+E → explorer.exe, common shortcuts
                    if key.lower() in ("win+e", "meta+e"):
                        step = {**step, "agent_type": "terminal", "action": "run",
                                "parameters": {"command": "explorer.exe"}, "name": "Open File Explorer"}
                    else:
                        step = {**step, "agent_type": "terminal", "action": "run",
                                "parameters": {"command": f"echo {key}"}, "name": f"Press {key}"}
                elif action == "click":
                    # Can't convert click to terminal — use file list instead
                    step = {**step, "agent_type": "file", "action": "list",
                            "parameters": {"path": os.path.expanduser("~")}, "name": "List home directory"}
                elif action == "type":
                    step = {**step, "agent_type": "terminal", "action": "run",
                            "parameters": {"command": f"echo {params.get('text', '')}"}}
            fixed.append(step)
        if fixed != steps:
            logger.info(f"Fixed {len(steps) - len([a for a, b in zip(steps, fixed) if a == b])} misplaced desktop steps")
        return fixed

    def _extract_search_query(self, prompt: str, triggers: List[str]) -> str:
        """Extract the actual search query from a prompt by stripping trigger phrases."""
        p = prompt.lower()
        # Strip common trigger phrases
        for phrase in [
            "search youtube for ", "search for ", "serach for ", "youtube search ",
            "search google for ", "google search ", "google ",
            "find on youtube ", "find ", "look up ", "look for ",
            "what is ", "what are ", "who is ", "how to ",
            "open youtube and search for ", "open youtube and ",
            "youtube ", "on youtube ",
        ]:
            if phrase in p:
                query = p.split(phrase, 1)[-1].strip()
                if query:
                    return query
        # Fallback: strip leading verbs/articles
        cleaned = re.sub(r'^(please |can you |could you |i want to |help me )', '', p).strip()
        return cleaned if cleaned else prompt

    def _extract_terminal_command(self, prompt: str) -> Optional[ExtractedCommand]:
        """Extract a terminal command from a prompt. Returns None if unclear."""
        p = prompt.lower().strip()
        # Direct command patterns
        # "ping google.com" / "ping google.com 5 times" / "ping google.com -n 5"
        ping_match = re.search(r'ping\s+(\S+)', p)
        if ping_match:
            host = ping_match.group(1)
            # Check if user specified count
            count_match = re.search(r'(\d+)\s*(?:times|packets|count)', p)
            if not count_match:
                count_match = re.search(r'-n\s+(\d+)', p)
            count = count_match.group(1) if count_match else "5"
            return ExtractedCommand(f"ping {host} -n {count}", False, "hardcoded_safe")

        # "ipconfig" / "ifconfig"
        if "ipconfig" in p:
            return ExtractedCommand("ipconfig", False, "hardcoded_safe")
        if "ifconfig" in p:
            return ExtractedCommand("ipconfig", False, "hardcoded_safe")

        # "disk space" / "disk usage"
        if any(k in p for k in ["disk space", "disk usage", "free space"]):
            return ExtractedCommand("wmic logicaldisk get size,freespace,caption", False, "hardcoded_safe")
        if any(k in p for k in ["system info", "system information"]):
            return ExtractedCommand("systeminfo", False, "hardcoded_safe")
        if any(k in p for k in ["running process", "list process", "processes"]):
            return ExtractedCommand('tasklist /FI "STATUS eq RUNNING"', False, "hardcoded_safe")
        if any(k in p for k in ["current directory", "where am i", "pwd"]):
            return ExtractedCommand("cd", False, "hardcoded_safe")

        # Quoted command: run "npm i" in the terminal...
        # ALWAYS requires confirmation — raw user input regardless of content
        quoted_match = re.search(r'''(?:run|execute|command)\s+["'](.+?)["']''', p)
        if quoted_match:
            return ExtractedCommand(quoted_match.group(1).strip(), True, "user_input_quoted")

        # Unquoted: run npm i in the terminal...
        # ALWAYS requires confirmation — raw user input regardless of content
        unquoted_match = re.search(r'''(?:run|execute|command)\s+(\S+(?:\s+\S+){0,5}?)\s+(?:in\s+(?:the\s+)?terminal|and\s+show|and\s+display|and\s+print)''', p)
        if unquoted_match:
            return ExtractedCommand(unquoted_match.group(1).strip(), True, "user_input_unquoted")

        # Known direct commands (no "run" prefix needed)
        known_cmds = ['npm', 'node', 'python', 'pip', 'git', 'docker', 'cargo', 'rustc', 'gcc', 'make', 'gradle',
                       'mvn', 'yarn', 'pnpm', 'bun', 'deno', 'curl', 'wget', 'ssh', 'scp', 'rsync',
                       'dir', 'ls', 'cat', 'type', 'echo', 'cls', 'clear', 'tree', 'find', 'where',
                       'netstat', 'tasklist', 'taskkill', 'regedit', 'sfc', 'chkdsk', 'defrag',
                       'format', 'diskpart', 'shutdown', 'restart', 'logoff', 'hostname']
        # Match "run npm install" or just "npm install" as direct command
        direct_match = re.search(r'(?:run\s+)?(\S+)(?:\s+(.+))?$', p)
        if direct_match:
            prog = direct_match.group(1)
            if prog in known_cmds:
                args = direct_match.group(2) or ""
                # Strip trailing natural language noise
                args = re.sub(r'\s+(?:in|on|the|terminal|and|show|display|print|results?|output|below|here).*$', '', args)
                cmd = f"{prog} {args}".strip()
                is_destructive = _is_destructive_command_string(cmd)
                return ExtractedCommand(cmd, is_destructive, "known_cmd")

        # Cannot extract a clear command — let LLM handle it
        return None

    async def _generate_rule_based_fallback(self, prompt: str) -> Dict[str, Any]:
        """Rule-based plan generator fallback when Ollama is offline or unavailable.
        Returns {"steps": [...]} with optional "pending_confirmation" for destructive commands."""
        prompt_lower = prompt.lower()

        # Send email tasks — check BEFORE read email to avoid "send an email" matching inbox
        email_intent = _parse_email_intent(prompt)
        if email_intent:
            to_email = email_intent["to"]
            subject = email_intent["subject"]
            body = email_intent["body"]
            # Generate proper email body via LLM (no timeout — let it finish)
            if body:
                try:
                    raw_body = body
                    generated = await llm_service.generate(
                        prompt=f"Write a professional email body about: {raw_body}\nDo NOT use any placeholders like [Name], [Date], [Company], [Your Name], [Phone], etc. Write all actual content with real text. Never use brackets.",
                        temperature=0.5,
                        max_tokens=300,
                    )
                    if generated:
                        cleaned = generated.strip()
                        # Remove any remaining [placeholder] lines
                        cleaned_lines = [
                            ln for ln in cleaned.split("\n")
                            if not (ln.strip().startswith("[") and ln.strip().endswith("]"))
                        ]
                        if cleaned_lines:
                            body = "\n".join(cleaned_lines).strip()
                            logger.info(f"LLM generated email body ({len(body)} chars)")
                except Exception as e:
                    logger.warning(f"LLM body generation failed ({e}), using raw text")
            if not subject and body:
                words = body.split()
                subject = " ".join(words[:5]) + ("..." if len(words) > 5 else "")
                # Remove trailing punctuation
                subject = subject.rstrip(".,!?;:")
            steps = [
                {
                    "step_id": "step_1",
                    "name": "Open Gmail inbox",
                    "agent_type": "browser",
                    "action": "navigate",
                    "parameters": {"url": "https://mail.google.com/mail/u/0/#inbox"}
                },
                {
                    "step_id": "step_2",
                    "name": "Click Compose button",
                    "agent_type": "browser",
                    "action": "click",
                    "parameters": {"selector": "div[role='button'][gh='cm'], div[aria-label*='Compose'], a[aria-label*='Compose'], .T-I.T-I-KE.L3", "fallback_text": "Compose"}
                },
                {
                    "step_id": "step_3",
                    "name": "Wait for compose panel to load",
                    "agent_type": "browser",
                    "action": "wait_for_selector",
                    "parameters": {"selector": "input[aria-label='To recipients'], input[name='subjectbox'], div[aria-label='New Message']", "timeout": 15}
                },
                {
                    "step_id": "step_4",
                    "name": "Fill recipient",
                    "agent_type": "browser",
                    "action": "fill",
                    "parameters": {"selector": "input[aria-label='To recipients'], textarea[name='to'], input[name='to']", "value": to_email}
                },
                {
                    "step_id": "step_5",
                    "name": "Press Tab to confirm recipient",
                    "agent_type": "browser",
                    "action": "press",
                    "parameters": {"key": "Tab"}
                },
                {
                    "step_id": "step_6",
                    "name": "Wait for subject field to be ready",
                    "agent_type": "browser",
                    "action": "wait_for_selector",
                    "parameters": {"selector": "input[name='subjectbox'], input[aria-label='Subject']", "timeout": 10}
                },
                {
                    "step_id": "step_7",
                    "name": "Fill subject",
                    "agent_type": "browser",
                    "action": "fill",
                    "parameters": {"selector": "input[name='subjectbox'], input[aria-label='Subject']", "value": subject}
                },
                {
                    "step_id": "step_8",
                    "name": "Fill email body",
                    "agent_type": "browser",
                    "action": "fill",
                    "parameters": {"selector": "div[role='textbox'][aria-label='Message Body'], div[aria-label='Message Body'], div[contenteditable='true']", "value": body}
                },
                {
                    "step_id": "step_9",
                    "name": "Wait for compose to settle",
                    "agent_type": "browser",
                    "action": "wait",
                    "parameters": {"seconds": 5}
                },
                {
                    "step_id": "step_10",
                    "name": "Click Send button",
                    "agent_type": "browser",
                    "action": "click",
                    "parameters": {"selector": "div[role='button'][data-tooltip*='Send (~Ctrl'], div[role='button'][aria-label*='Send (~Ctrl'], div[role='button'][data-tooltip*='Send'], div[role='button'][aria-label='Send']", "fallback_text": "Send"}
                },
                {
                    "step_id": "step_11",
                    "name": "Wait for sent confirmation",
                    "agent_type": "browser",
                    "action": "wait",
                    "parameters": {"seconds": 3}
                },
            ]
            return steps

        # YouTube search tasks
        is_youtube_search = (
            ("youtube" in prompt_lower or "video" in prompt_lower)
            and ("search" in prompt_lower or "find" in prompt_lower or "look" in prompt_lower or "watch" in prompt_lower)
        )
        if is_youtube_search:
            query = self._extract_search_query(prompt, [])
            wants_summary = any(k in prompt_lower for k in ["summarize", "summary", "sumarize", "summrize", "and summarize", "and sum up"])
            steps = [
                {
                    "step_id": "step_1",
                    "name": "Navigate to YouTube",
                    "agent_type": "browser",
                    "action": "navigate",
                    "parameters": {"url": "https://www.youtube.com"}
                },
                {
                    "step_id": "step_2",
                    "name": "Search on YouTube",
                    "agent_type": "browser",
                    "action": "fill",
                    "parameters": {"selector": "input[name='search_query']", "value": query}
                },
                {
                    "step_id": "step_3",
                    "name": "Submit search",
                    "agent_type": "browser",
                    "action": "press",
                    "parameters": {"key": "Enter"}
                },
                {
                    "step_id": "step_4",
                    "name": "Extract video links",
                    "agent_type": "browser",
                    "action": "scrape_links",
                    "parameters": {"count": 5, "domain": "youtube.com/watch"}
                },
            ]
            if wants_summary:
                steps.extend([
                    {
                        "step_id": "step_5",
                        "name": "Wait for results to load",
                        "agent_type": "browser",
                        "action": "wait",
                        "parameters": {"seconds": 3}
                    },
                    {
                        "step_id": "step_6",
                        "name": "Scrape search results content",
                        "agent_type": "browser",
                        "action": "scrape_text",
                        "parameters": {}
                    },
                    {
                        "step_id": "step_7",
                        "name": "Summarize findings",
                        "agent_type": "browser",
                        "action": "summarize",
                        "parameters": {"query": f"Summarize the top video search results for: {query}. List each video title with its key topic or takeaway. Focus on the most important news or information."}
                    },
                ])
            return steps

        # Terminal / command tasks — check BEFORE Google to avoid "ping google.com" matching Google
        if any(k in prompt_lower for k in ["terminal", "ping", "command", "shell", "powershell", "cmd",
                                            "system info", "disk space", "running process", "tasklist",
                                            "ipconfig", "processes"]):
            result = self._extract_terminal_command(prompt)
            if result is None:
                # Could not extract a clear command — let LLM handle it
                return {"steps": []}
            step = {
                "step_id": "step_1",
                "name": f"Run: {result.command}",
                "agent_type": "terminal",
                "action": "run",
                "parameters": {"command": result.command}
            }
            if result.requires_confirmation:
                return {
                    "steps": [step],
                    "pending_confirmation": {
                        "type": "terminal_command",
                        "command": result.command,
                        "message": f"The command '{result.command}' requires your confirmation before execution.",
                        "source": result.source_path,
                    }
                }
            return {"steps": [step]}

        # File creation tasks — check BEFORE desktop/Google since "on my desktop" matches desktop
        is_file_creation = (
            "create file" in prompt_lower
            or "write file" in prompt_lower
            or "make file" in prompt_lower
            or ("create" in prompt_lower and "file" in prompt_lower)
            or ("write" in prompt_lower and "file" in prompt_lower)
            or ("make" in prompt_lower and "file" in prompt_lower)
        )
        # Code generation requests need the LLM — rule-based can't write real code
        code_keywords = [
            "code", "function", "script", "program", "algorithm", "class ",
            "factorial", "fibonacci", "sort", "palindrome", "binary", "search",
            "queue", "stack", "linked list", "tree", "graph", "hash",
            "recursion", "loop", "iterate", "implement", "write a",
            "calculator", "converter", "generator", "parser", "analyzer",
            "flask", "django", "fastapi", "api", "web scraper", "crawler",
            "game", "tic tac", "snake", "chat", "server", "client",
            "hello world", "print", "input", "loop", "array", "list",
            "dictionary", "string", "number", "math", "pattern",
        ]
        is_code_request = (
            any(k in prompt_lower for k in code_keywords)
            or bool(re.search(r'\b(?:python|javascript|typescript|java|c\+\+|ruby|go|rust|php|html|css|sql|bash|shell)\b', prompt_lower))
            or bool(re.search(r'\.\w{1,4}\b', prompt_lower))  # file extensions like .py, .js
        )
        if is_file_creation:
            # Use LLM metadata for filename and target directory
            metadata = await _extract_prompt_metadata(prompt)

            if metadata.get("filename"):
                filename = metadata["filename"]
            else:
                # Fallback: regex extraction
                file_match = re.search(r'(?:named?|called?|as)\s+["\']?(\S+\.\w+)["\']?', prompt_lower)
                if file_match:
                    filename = file_match.group(1)
                else:
                    name_match = re.search(r'(?:file|script|program)\s+(?:for|with|called|named)\s+(\w+)', prompt_lower)
                    if name_match:
                        base_name = name_match.group(1)
                    else:
                        base_name = "aco_output"
                    lang_def = LanguageDetector.detect(prompt)
                    ext = lang_def.extension
                    ts = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"{base_name}_{ts}{ext}"

            # For code requests, use LLM to generate real code content
            content = "Created by ACO Agent"
            if is_code_request:
                lang_def = LanguageDetector.detect(prompt)
                if metadata.get("language"):
                    detected = _NAME_TO_DEF.get(metadata["language"].lower())
                    if detected:
                        lang_def = detected
                try:
                    code_prompt = (
                        f"Generate the complete, working {lang_def.name.upper()} code for this request: '{prompt}'\n"
                        f"Return ONLY the raw code. No markdown, no explanation, no fences."
                    )
                    generated = await llm_service.generate(
                        prompt=code_prompt,
                        temperature=0.3,
                        max_tokens=4096,
                    )
                    if generated and len(generated.strip()) > 10:
                        content = generated.strip()
                        logger.info(f"LLM generated code content ({len(content)} chars)")
                except Exception as e:
                    logger.warning(f"LLM code generation failed: {e}, using fallback content")
            else:
                content_match = re.search(r'(?:with content|containing|saying|that says|that contains)\s+["\']?(.+?)["\']?\s*$', prompt)
                if content_match:
                    content = content_match.group(1)

            # Resolve target directory from metadata
            target_path = None
            if metadata.get("target_directory"):
                target_path = os.path.join(get_user_dir(metadata["target_directory"]), filename)
            # Fallback: regex path detection
            if not target_path:
                for keyword in ["desktop", "documents", "downloads", "pictures", "music", "videos"]:
                    if f"on my {keyword}" in prompt_lower or f"in my {keyword}" in prompt_lower or f"to my {keyword}" in prompt_lower or f"in {keyword}" in prompt_lower:
                        target_path = os.path.join(get_user_dir(keyword), filename)
                        break
            # Also handle explicit paths like ~/Desktop or %USERPROFILE%\Desktop
            if not target_path:
                path_match = re.search(r'(?:on|in|to|at)\s+((?:~|%USERPROFILE%|%HOME%)[\\/]\S+)', prompt)
                if path_match:
                    raw = path_match.group(1).strip('"\'')
                    target_path = os.path.expanduser(os.path.expandvars(raw))
                    if not target_path.endswith(filename):
                        target_path = os.path.join(target_path, filename)

            result = {"steps": [
                {
                    "step_id": "step_1",
                    "name": f"Create file: {target_path or filename}",
                    "agent_type": "file",
                    "action": "write",
                    "parameters": {"path": target_path, "content": content} if target_path else {"filename": filename, "content": content}
                }
            ]}

            # Add pending_confirmation for file writes
            file_path_display = target_path or f"~/ACO_Output/{filename}"
            result["pending_confirmation"] = {
                "type": "file_write",
                "path": file_path_display,
                "message": f"ACO wants to create file at {file_path_display}. Allow?",
            }
            return result

        # Desktop / click tasks (only when NOT about file creation)
        if any(k in prompt_lower for k in ["click", "mouse"]):
            return {"steps": [
                {
                    "step_id": "step_1",
                    "name": "Click target screen coords",
                    "agent_type": "desktop",
                    "action": "click",
                    "parameters": {"x": 500, "y": 400}
                }
            ]}

        # File search by extension tasks — check BEFORE generic directory listing
        ext_match = re.search(r'(?:find|get|list|show|search)\s+(?:all\s+)?(?:my\s+)?(\w+)\s*(?:files?|docs?|documents?)', prompt_lower)
        if not ext_match:
            ext_match = re.search(r'(?:all|any)\s+(\w+)\s+files?', prompt_lower)
        is_find_by_ext = ext_match and ext_match.group(1) in [
            "pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "gif", "bmp",
            "mp3", "mp4", "avi", "mkv", "wav", "flac",
            "zip", "rar", "7z", "tar", "gz",
            "py", "js", "ts", "java", "cpp", "c", "rs", "go", "rb", "php",
            "html", "css", "json", "xml", "yaml", "yml", "toml", "csv", "xlsx", "xls",
            "ppt", "pptx", "md", "log", "exe", "msi", "dll",
        ]
        if is_find_by_ext:
            ext = ext_match.group(1).lower()
            target_path = None
            for keyword in ["desktop", "documents", "downloads", "pictures", "music", "videos"]:
                if keyword in prompt_lower:
                    target_path = get_user_dir(keyword)
                    break
            if target_path is None:
                target_path = get_user_dir("desktop")
            recursive = any(k in prompt_lower for k in ["recursive", "all subfolder", "subfolder", "all folders", "entire"])
            return {"steps": [
                {
                    "step_id": "step_1",
                    "name": f"Find all .{ext} files in {target_path}",
                    "agent_type": "file",
                    "action": "list",
                    "parameters": {"path": target_path, "extension": ext, "recursive": recursive}
                }
            ]}

        # Directory listing tasks — use regex to handle "show all files", "list my files", etc.
        is_list_dir = bool(re.search(r'(?:list|show|display)\s+(?:all\s+)?(?:the\s+)?(?:my\s+)?(?:files?|contents?|items?)', prompt_lower)) or bool(re.search(r'(?:list|show)\s+(?:all\s+)?(?:the\s+)?(?:my\s+)?(?:directory|directory|folder)', prompt_lower)) or any(k in prompt_lower for k in ["what's in", "what is in", "files in", "files on"])
        if is_list_dir:
            # First check known directories
            target_path = None
            for keyword in ["desktop", "documents", "downloads", "pictures", "music", "videos"]:
                if keyword in prompt_lower:
                    target_path = get_user_dir(keyword)
                    break
            # If no known directory matched, try to find a folder by name in home
            if target_path is None or target_path == os.path.expanduser("~"):
                # Extract folder name from patterns like "in my coursera folder", "in src", "in projects folder"
                folder_match = re.search(r'(?:in|on|from|under)\s+(?:my\s+)?(\S+?)(?:\s+folder|\s+dir|\s+directory)?(?:\s+in\s+.+)?(?:\s*$)', prompt_lower)
                if folder_match:
                    folder_name = folder_match.group(1)
                    home = os.path.expanduser("~")
                    # Try exact match first, then case-insensitive
                    candidate = os.path.join(home, folder_name)
                    if os.path.isdir(candidate):
                        target_path = candidate
                    else:
                        # Search home directory for matching folder (case-insensitive)
                        try:
                            for entry in os.listdir(home):
                                if entry.lower() == folder_name.lower() and os.path.isdir(os.path.join(home, entry)):
                                    target_path = os.path.join(home, entry)
                                    break
                        except OSError:
                            pass
            if target_path is None:
                target_path = os.path.expanduser("~")
            # Extract limit (e.g. "last 10", "top 5")
            limit = 0
            limit_match = re.search(r'(?:last|top|latest|recent)\s+(\d+)', prompt_lower)
            if limit_match:
                limit = int(limit_match.group(1))
            params: Dict[str, Any] = {"path": target_path}
            if limit > 0:
                params["limit"] = limit
            return {"steps": [
                {
                    "step_id": "step_1",
                    "name": f"List directory: {target_path}" + (f" (last {limit})" if limit else ""),
                    "agent_type": "file",
                    "action": "list",
                    "parameters": params
                }
            ]}

        # Read file from user directory
        is_read_file = any(k in prompt_lower for k in ["read file", "open file", "show file"])
        if is_read_file:
            target_path = None
            for keyword in ["desktop", "documents", "downloads"]:
                if keyword in prompt_lower:
                    target_path = get_user_dir(keyword)
                    break
            file_match = re.search(r'(?:named?|called?|as)\s+["\']?(\S+\.\w+)["\']?', prompt_lower)
            if file_match and target_path:
                target_path = os.path.join(target_path, file_match.group(1))
            elif file_match:
                target_path = file_match.group(1)
            if target_path:
                return {"steps": [
                    {
                        "step_id": "step_1",
                        "name": f"Read file: {target_path}",
                        "agent_type": "file",
                        "action": "read",
                        "parameters": {"path": target_path}
                    }
                ]}

        # Google / web search tasks
        if any(k in prompt_lower for k in ["google", "search for", "serach for", "look up", "what is", "what are", "who is", "how to"]):
            query = self._extract_search_query(prompt, ["google", "search for", "serach for", "look up", "what is", "what are", "who is", "how to"])
            steps = [
                {
                    "step_id": "step_1",
                    "name": "Navigate to Google",
                    "agent_type": "browser",
                    "action": "navigate",
                    "parameters": {"url": "https://www.google.com"}
                },
                {
                    "step_id": "step_2",
                    "name": "Search on Google",
                    "agent_type": "browser",
                    "action": "fill",
                    "parameters": {"selector": "input[name='q']", "value": query}
                },
                {
                    "step_id": "step_3",
                    "name": "Submit search",
                    "agent_type": "browser",
                    "action": "press",
                    "parameters": {"key": "Enter"}
                }
            ]
            if any(k in prompt_lower for k in ["summarize", "summary", "sumarize", "summrize"]):
                steps.append({
                    "step_id": "step_4",
                    "name": "Scrape and summarize search results",
                    "agent_type": "browser",
                    "action": "summarize",
                    "parameters": {"query": prompt}
                })
            else:
                steps.append({
                    "step_id": "step_4",
                    "name": "Scrape search results",
                    "agent_type": "browser",
                    "action": "scrape_text",
                    "parameters": {}
                })
            return {"steps": steps}

        # Website / URL navigation
        if any(k in prompt_lower for k in ["website", "http://", "https://", "open "]):
            url_match = re.search(r'(https?://\S+)', prompt)
            if url_match:
                url = url_match.group(1)
            elif "open " in prompt_lower:
                site = prompt_lower.split("open ", 1)[-1].strip().split()[0]
                url = f"https://www.{site}.com"
            else:
                url = "https://www.google.com"
            steps = [
                {
                    "step_id": "step_1",
                    "name": f"Navigate to {url}",
                    "agent_type": "browser",
                    "action": "navigate",
                    "parameters": {"url": url}
                }
            ]
            if any(k in prompt_lower for k in ["summarize", "summary", "sumarize"]):
                steps.append({
                    "step_id": "step_2",
                    "name": "Summarize page content",
                    "agent_type": "browser",
                    "action": "summarize",
                    "parameters": {"query": prompt}
                })
            else:
                steps.append({
                    "step_id": "step_2",
                    "name": "Scrape page content",
                    "agent_type": "browser",
                    "action": "scrape_text",
                    "parameters": {}
                })
            return {"steps": steps}

        # File search tasks
        if any(k in prompt_lower for k in ["spreadsheet", "excel", "csv", "document"]):
            return {"steps": [
                {
                    "step_id": "step_1",
                    "name": "Search for file on disk",
                    "agent_type": "file",
                    "action": "find_text",
                    "parameters": {"text": prompt}
                }
            ]}

        # Generic fallback — return empty to signal LLM needed
        return {"steps": []}

# Export global planner service
planner_service = PlannerService()
