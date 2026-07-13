import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SandboxSecurityError(PermissionError):
    pass

class PluginSandbox:
    def __init__(self):
        # Establish restricted builtins to isolate plugin runtimes
        self._allowed_builtins = {
            "abs": abs,
            "all": all,
            "any": any,
            "bool": bool,
            "dict": dict,
            "float": float,
            "int": int,
            "len": len,
            "list": list,
            "map": map,
            "max": max,
            "min": min,
            "range": range,
            "round": round,
            "set": set,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "zip": zip
        }

    def execute(self, code_str: str, entry_point: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes Python code in a restricted global environment context.
        Prevents raw system file manipulation or native package execution.
        """
        logger.info(f"Sandbox compiling plugin entry point: {entry_point}")
        
        # Enforce lexical checks on code string to block basic safety violations
        forbidden_keywords = ["__import__", "open", "eval", "exec", "subprocess", "os", "sys", "socket"]
        for keyword in forbidden_keywords:
            if keyword in code_str:
                raise SandboxSecurityError(f"Plugin code contains forbidden expression: '{keyword}'")

        # Create isolated execution dictionary context
        sandbox_globals = {
            "__builtins__": self._allowed_builtins
        }
        sandbox_locals = {}

        try:
            # Compile and execute the plugin code
            compiled_code = compile(code_str, "<plugin_sandbox>", "exec")
            exec(compiled_code, sandbox_globals, sandbox_locals)

            # Check if entry point function is defined
            if entry_point not in sandbox_locals:
                raise NameError(f"Entry point function '{entry_point}' not found in compiled code.")

            target_func = sandbox_locals[entry_point]
            if not callable(target_func):
                raise TypeError(f"'{entry_point}' is not a callable function.")

            # Invoke target plugin inside sandboxed scope
            result = target_func(inputs)
            return {"success": True, "result": result}

        except Exception as e:
            logger.error(f"Plugin Sandbox execution failure: {e}")
            return {"success": False, "error": str(e)}

plugin_sandbox = PluginSandbox()
