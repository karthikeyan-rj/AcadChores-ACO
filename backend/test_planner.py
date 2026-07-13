import httpx
import json

system = (
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
    "OUTPUT: ONLY a JSON array. No markdown. No text. Just the array.\n"
)

prompt = "User request: 'summarize the last 5 emails of me'\nDetected intent: browser_search\nGenerate a complete multi-step plan. Return ONLY the JSON array."

print("Sending to Ollama...")
resp = httpx.post("http://localhost:11434/api/generate", json={
    "model": "qwen2.5-coder:7b",
    "system": system,
    "prompt": prompt,
    "stream": False,
    "format": "json",
    "options": {"temperature": 0.0, "num_predict": 4096}
}, timeout=120)
data = resp.json()
raw = data.get("response", "")
print(f"\n=== RAW LLM OUTPUT ({len(raw)} chars) ===")
print(raw)
print("\n=== PARSED ===")
try:
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        keys = list(parsed.keys())
        print(f"Dict with keys: {keys}")
        if "steps" in parsed and isinstance(parsed["steps"], list):
            steps = parsed["steps"]
            print(f"Found 'steps' key with {len(steps)} steps:")
            for s in steps:
                print(f"  {s.get('step_id')}: {s.get('agent_type')}/{s.get('action')} - {s.get('name')}")
        else:
            print("SINGLE STEP - no 'steps' key found")
    elif isinstance(parsed, list):
        print(f"Array with {len(parsed)} steps:")
        for s in parsed:
            print(f"  {s.get('step_id')}: {s.get('agent_type')}/{s.get('action')} - {s.get('name')}")
except Exception as e:
    print(f"Parse error: {e}")
