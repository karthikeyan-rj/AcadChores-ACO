"""Process manager for tracking and terminating running subprocesses.

Provides execution-scoped process tracking so that cancellation can
terminate the correct process tree without affecting unrelated system
processes.
"""
import os
import sys
import signal
import logging
import subprocess
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# execution_id -> subprocess.Popen handle
_running_processes: Dict[str, subprocess.Popen] = {}


def register_process(execution_id: str, proc: subprocess.Popen) -> None:
    """Register a subprocess for the given execution."""
    _running_processes[execution_id] = proc
    logger.info(f"ProcessManager: registered PID {proc.pid} for execution {execution_id}")


def unregister_process(execution_id: str) -> None:
    """Remove a process from the registry (call after completion)."""
    _running_processes.pop(execution_id, None)


def cancel_process(execution_id: str) -> bool:
    """Terminate the process tree for the given execution.

    On Windows, uses taskkill /F /T to kill the entire process tree.
    On POSIX, sends SIGTERM then SIGKILL after a short grace period.

    Returns True if a process was found and termination was attempted.
    """
    proc = _running_processes.pop(execution_id, None)
    if proc is None:
        logger.info(f"ProcessManager: no tracked process for execution {execution_id}")
        return False

    pid = proc.pid
    logger.info(f"ProcessManager: terminating PID {pid} for execution {execution_id}")

    try:
        if sys.platform == "win32":
            # taskkill /F /T: force-kill the entire process tree
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                capture_output=True,
                timeout=10,
            )
        else:
            # POSIX: try SIGTERM on the process group, then SIGKILL
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
    except Exception as e:
        logger.warning(f"ProcessManager: error killing PID {pid}: {e}")

    return True


def cancel_all() -> int:
    """Terminate all tracked processes. Returns count terminated."""
    count = 0
    for eid in list(_running_processes.keys()):
        if cancel_process(eid):
            count += 1
    return count


def is_process_running(execution_id: str) -> bool:
    """Check if the tracked process for an execution is still alive."""
    proc = _running_processes.get(execution_id)
    if proc is None:
        return False
    return proc.poll() is None
