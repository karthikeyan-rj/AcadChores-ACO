import json
import logging
import time
from typing import Optional, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
}

WORKFLOW_SCHEMA = """You are a workflow planner for a desktop automation system.
Given a user request, output a JSON workflow with this EXACT structure:

{
  "steps": [
    {
      "step_id": "step_1",
      "name": "descriptive name",
      "agent_type": "agent_type",
      "action": "action_name",
      "parameters": {"param": "value"},
      "reason": "brief reason"
    }
  ]
}

Agent types: browser, browser_agent, application, application_agent, filesystem, file_system, file_system_agent, computer, computer_agent, messaging, messaging_agent, media, media_agent, email, email_agent, calendar, calendar_agent, ai_assistant, ai_assistant_agent.

Browser actions: search, click, navigate, type, scroll, select, open, close.
Application actions: open, close, focus, minimize, maximize.
Filesystem actions: read, write, create, delete, move, copy, list, search.
Computer actions: screenshot, mouse_click, mouse_move, type_text, press_key, hotkey, scroll.
Email actions: send, read, search, compose, reply.

Rules:
- Every step must have a step_id, name, agent_type, action.
- step_ids must be unique and sequential: "step_1", "step_2", etc.
- Use "reason" field to explain why each step exists.
- Output ONLY valid JSON — no markdown, no code fences, no explanation.
"""


class CloudPlannerResult:
    def __init__(self, success: bool, workflow: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None, tokens_input: int = 0,
                 tokens_output: int = 0, latency_ms: float = 0.0):
        self.success = success
        self.workflow = workflow
        self.error = error
        self.tokens_input = tokens_input
        self.tokens_output = tokens_output
        self.latency_ms = latency_ms


async def generate_cloud_workflow(prompt: str, api_key: str, provider: str = "openai",
                                   model: str = "gpt-4o-mini", timeout: float = 60.0) -> CloudPlannerResult:
    start = time.time()
    if not api_key:
        return CloudPlannerResult(success=False, error="No API key provided", latency_ms=(time.time() - start) * 1000)
    provider = provider.lower().strip()
    if provider not in PROVIDER_URLS:
        return CloudPlannerResult(success=False, error=f"Unsupported provider: {provider}", latency_ms=(time.time() - start) * 1000)

    messages_content = f"{WORKFLOW_SCHEMA}\n\nUser request: {prompt}"
    try:
        if provider == "openai":
            result = await _call_openai(api_key, model, messages_content, timeout)
        elif provider == "anthropic":
            result = await _call_anthropic(api_key, model, messages_content, timeout)
        elif provider == "gemini":
            result = await _call_gemini(api_key, model, messages_content, timeout)
        else:
            result = CloudPlannerResult(success=False, error=f"Provider {provider} not implemented", latency_ms=(time.time() - start) * 1000)
    except httpx.TimeoutException:
        latency = (time.time() - start) * 1000
        result = CloudPlannerResult(success=False, error="Cloud API request timed out", latency_ms=latency)
    except Exception as e:
        latency = (time.time() - start) * 1000
        result = CloudPlannerResult(success=False, error=f"Cloud API error: {str(e)[:200]}", latency_ms=latency)

    if result.success and result.workflow:
        result.workflow["planner_source"] = "cloud_fallback"
    return result


async def _call_openai(api_key: str, model: str, messages_content: str, timeout: float) -> CloudPlannerResult:
    start = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            PROVIDER_URLS["openai"],
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": messages_content}], "temperature": 0.1, "max_tokens": 4000},
        )
    if resp.status_code != 200:
        return CloudPlannerResult(success=False, error=f"OpenAI error {resp.status_code}: {resp.text[:200]}",
                                  latency_ms=(time.time() - start) * 1000)
    data = resp.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens_in = usage.get("prompt_tokens", 0)
    tokens_out = usage.get("completion_tokens", 0)
    return _parse_workflow_json(text, tokens_in, tokens_out, (time.time() - start) * 1000)


async def _call_anthropic(api_key: str, model: str, messages_content: str, timeout: float) -> CloudPlannerResult:
    start = time.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            PROVIDER_URLS["anthropic"],
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json={"model": model, "max_tokens": 4000, "messages": [{"role": "user", "content": messages_content}]},
        )
    if resp.status_code != 200:
        return CloudPlannerResult(success=False, error=f"Anthropic error {resp.status_code}: {resp.text[:200]}",
                                  latency_ms=(time.time() - start) * 1000)
    data = resp.json()
    text = data["content"][0]["text"]
    usage = data.get("usage", {})
    tokens_in = usage.get("input_tokens", 0)
    tokens_out = usage.get("output_tokens", 0)
    return _parse_workflow_json(text, tokens_in, tokens_out, (time.time() - start) * 1000)


async def _call_gemini(api_key: str, model: str, messages_content: str, timeout: float) -> CloudPlannerResult:
    start = time.time()
    url = PROVIDER_URLS["gemini"].format(model=model)
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{url}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": messages_content}]}], "generationConfig": {"temperature": 0.1, "maxOutputTokens": 4000}},
        )
    if resp.status_code != 200:
        return CloudPlannerResult(success=False, error=f"Gemini error {resp.status_code}: {resp.text[:200]}",
                                  latency_ms=(time.time() - start) * 1000)
    data = resp.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    tokens_in = usage.get("promptTokenCount", 0)
    tokens_out = usage.get("candidatesTokenCount", 0)
    return _parse_workflow_json(text, tokens_in, tokens_out, (time.time() - start) * 1000)


def _parse_workflow_json(text: str, tokens_in: int, tokens_out: int, latency_ms: float) -> CloudPlannerResult:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines)
    try:
        workflow = json.loads(cleaned)
    except json.JSONDecodeError:
        return CloudPlannerResult(success=False, error=f"Cloud API returned invalid JSON: {cleaned[:200]}",
                                  tokens_input=tokens_in, tokens_output=tokens_out, latency_ms=latency_ms)
    if "steps" not in workflow or not isinstance(workflow["steps"], list):
        return CloudPlannerResult(success=False, error="Workflow missing 'steps' list",
                                  tokens_input=tokens_in, tokens_output=tokens_out, latency_ms=latency_ms)
    return CloudPlannerResult(success=True, workflow=workflow, tokens_input=tokens_in, tokens_output=tokens_out, latency_ms=latency_ms)
