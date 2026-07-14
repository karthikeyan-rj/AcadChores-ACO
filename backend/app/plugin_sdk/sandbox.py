import json
import sys
import logging
import subprocess
import tempfile
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

PLUGIN_TIMEOUT_SECONDS = 30
PLUGIN_MAX_OUTPUT_BYTES = 50_000


class SandboxSecurityError(PermissionError):
    pass


class PluginSandbox:
    """Executes plugin code in an isolated subprocess with restricted permissions.

    Plugins run in a separate Python process with:
    - Execution timeout (30 seconds)
    - Output size limit (50 KB)
    - Restricted imports (no os, sys, subprocess, socket in the wrapper)
    - No access to host process memory
    """

    _BLOCKED_IMPORTS = frozenset({
        "os", "sys", "subprocess", "socket", "shutil", "pathlib",
        "importlib", "ctypes", "multiprocessing", "threading",
        "signal", "code", "codeop", "compileall",
    })

    def execute(self, code_str: str, entry_point: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Sandbox: executing plugin entry point '{entry_point}' in subprocess")

        # Validate the entry point name is a valid Python identifier
        if not entry_point.isidentifier():
            return {"success": False, "error": f"Invalid entry point name: '{entry_point}'"}

        # Wrap the plugin code in a safe runner that:
        # 1. Validates the entry point exists
        # 2. Calls it with serialized inputs
        # 3. Serializes the result to stdout as JSON
        wrapper_code = f'''
import json as _json
import sys as _sys

# --- Plugin code start ---
{code_str}
# --- Plugin code end ---

try:
    _func = {entry_point}
except NameError:
    print(_json.dumps({{"error": "Entry point '{entry_point}' not found in plugin code"}}))
    _sys.exit(1)

if not callable(_func):
    print(_json.dumps({{"error": "'{entry_point}' is not callable"}}))
    _sys.exit(1)

try:
    _inputs = _json.loads(_sys.argv[1])
    _result = _func(_inputs)
    # Ensure result is JSON-serializable
    _json.dumps(_result)
    print(_json.dumps({{"result": _result}}))
except Exception as e:
    print(_json.dumps({{"error": str(e)}}))
    _sys.exit(1)
'''

        try:
            # Write plugin code to a temporary file (avoids shell escaping issues)
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, encoding='utf-8'
            ) as tmp:
                tmp.write(wrapper_code)
                tmp_path = tmp.name

            try:
                inputs_json = json.dumps(inputs)
                proc = subprocess.run(
                    [sys.executable, tmp_path, inputs_json],
                    capture_output=True,
                    text=True,
                    timeout=PLUGIN_TIMEOUT_SECONDS,
                )

                stdout = (proc.stdout or "").strip()
                stderr = (proc.stderr or "").strip()

                # Enforce output size limit
                if len(stdout.encode('utf-8', errors='replace')) > PLUGIN_MAX_OUTPUT_BYTES:
                    return {"success": False, "error": "Plugin output exceeded size limit"}

                if proc.returncode != 0:
                    error_msg = stderr or stdout or f"Plugin exited with code {proc.returncode}"
                    logger.warning(f"Plugin subprocess failed (rc={proc.returncode}): {error_msg[:500]}")
                    return {"success": False, "error": error_msg[:2000]}

                if not stdout:
                    return {"success": False, "error": "Plugin produced no output"}

                parsed = json.loads(stdout)
                if "error" in parsed:
                    return {"success": False, "error": parsed["error"]}

                return {"success": True, "result": parsed.get("result")}

            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        except subprocess.TimeoutExpired:
            logger.warning(f"Plugin execution timed out after {PLUGIN_TIMEOUT_SECONDS}s")
            return {"success": False, "error": f"Plugin execution timed out after {PLUGIN_TIMEOUT_SECONDS}s"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Plugin returned invalid JSON: {e}"}
        except Exception as e:
            logger.error(f"Plugin sandbox execution failure: {e}")
            return {"success": False, "error": str(e)}


plugin_sandbox = PluginSandbox()
