import requests, json

URL = "http://localhost:8001/api/v1/workflows/generate-plan"

prompts = [
    "ping google.com",
    "what is the disk space on my computer",
    "open google and summarize what python is",
    "create a file called notes.txt with today todo list",
    "format the drive",
    "list all files on my desktop",
]

baseline = {}
for i, p in enumerate(prompts):
    print(f"=== Prompt {i+1}: {p} ===")
    try:
        r = requests.post(URL, json={"prompt": p}, timeout=120)
        data = r.json()
        steps = data.get("steps", [])
        pending = data.get("pending_confirmation")
        print(f"  Steps: {len(steps)}")
        for s in steps:
            at = s.get("agent_type", "?")
            ac = s.get("action", "?")
            nm = s.get("name", "?")
            prms = list(s.get("parameters", {}).keys())
            print(f"  [{at}/{ac}] {nm}  params={prms}")
        if pending:
            print(f"  pending_confirmation: {json.dumps(pending)}")
        else:
            print("  pending_confirmation: None")
        baseline[p] = {"count": len(steps), "types": [(s.get("agent_type"), s.get("action")) for s in steps]}
    except Exception as e:
        print(f"  ERROR: {e}")
        baseline[p] = {"count": -1, "error": str(e)}
    print()

print("=" * 60)
print("BASELINE SUMMARY (post-fix)")
print("=" * 60)
for p, b in baseline.items():
    print(f"  {p}: {b['count']} steps, types={b.get('types', b.get('error'))}")
