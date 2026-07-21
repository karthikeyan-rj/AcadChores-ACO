import json
import sys
import logging
import asyncio
import traceback
from typing import Dict, Any, Optional
from uuid import uuid4
from datetime import datetime, timezone

from app.core.database import db_manager
from app.core.event_bus import event_bus
from app.verification import verification_engine
from app.ai.capabilities import capability_registry

logger = logging.getLogger(__name__)

_in_memory_task_queue: asyncio.Queue = asyncio.Queue()
_in_memory_task_statuses: Dict[str, Dict[str, str]] = {}

# Maximum time a single task can run before being cancelled (5 minutes)
TASK_EXECUTION_TIMEOUT: float = 300.0

# Maximum in-memory task entries before cleanup
_MAX_IN_MEMORY_TASKS = 500


def _get_error_suggestion(error_type: str, error_msg: str, step_data: Dict[str, Any]) -> str:
    """Generate a human-readable suggestion based on the error type and context."""
    agent = step_data.get("agent_type", "")
    action = step_data.get("action", "")
    params = step_data.get("parameters", {})

    if error_type == "PermissionError":
        return "This action requires your permission. Check if a permission prompt appeared."
    if error_type == "FileNotFoundError":
        if agent == "file":
            path = params.get("path", params.get("source", "the target path"))
            return f"The file or directory '{path}' was not found. Verify the path is correct."
        return "A required file or resource was not found."
    if error_type == "FileExistsError":
        return "A file already exists at the target location. Use a different name or delete the existing file first."
    if error_type == "IsADirectoryError":
        return "Expected a file but found a directory. Use 'list' action to inspect directory contents."
    if error_type == "TimeoutError":
        return f"The {agent} action timed out. The server may be slow or the resource unavailable. Try again later."
    if error_type == "RuntimeError":
        if "Could not click" in error_msg:
            return "The target element could not be found on the page. The page layout may have changed."
        if "Could not fill" in error_msg:
            return "No matching input field found. The form structure may have changed."
        if "Failed to navigate" in error_msg:
            return "Navigation failed. Check the URL and your network connection."
        if "Failed to launch browser" in error_msg:
            return "Browser failed to start. Try restarting the backend service."
        if "deletion verification failed" in error_msg:
            return "File deletion could not be verified. Check file permissions."
        return f"Runtime error during {agent}/{action}. Check the execution log for details."
    if error_type == "ValueError":
        return f"Invalid input for {agent}/{action}. Check the parameters."
    if error_type == "OSError" or error_type == "IOError":
        return f"File system error during {action}. Check file permissions and disk space."
    if error_type == "asyncio.TimeoutError":
        return f"The {agent} task exceeded the time limit. Try breaking the task into smaller steps."

    return f"An unexpected error occurred during {agent}/{action}. Check the execution log."


def _cleanup_task_statuses():
    """Evict oldest completed/failed task statuses if dict grows too large."""
    if len(_in_memory_task_statuses) > _MAX_IN_MEMORY_TASKS:
        keys = list(_in_memory_task_statuses.keys())
        for k in keys[: len(keys) // 2]:
            status = _in_memory_task_statuses.get(k, {}).get("status", "")
            if status in ("completed", "failed"):
                _in_memory_task_statuses.pop(k, None)

class TaskQueue:
    @staticmethod
    async def enqueue(execution_id: str, step_data: Dict[str, Any]) -> str:
        redis = db_manager.redis_client
        task_id = str(uuid4())
        
        task_payload = {
            "task_id": task_id,
            "execution_id": execution_id,
            "step_data": step_data,
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        status_mapping = {
            "status": "queued",
            "execution_id": execution_id,
            "created_at": task_payload["created_at"],
            "progress": "0",
            "result": ""
        }

        if redis:
            await redis.hset(f"task:status:{task_id}", mapping=status_mapping)
            await redis.rpush("queue:tasks", json.dumps(task_payload))
        else:
            _in_memory_task_statuses[task_id] = status_mapping
            logger.info(f"Queue: enqueue task_id={task_id} queue.id={id(_in_memory_task_queue)} qsize_before={_in_memory_task_queue.qsize()}")
            await _in_memory_task_queue.put(json.dumps(task_payload))
            logger.info(f"Queue: put OK, qsize_after={_in_memory_task_queue.qsize()}")
        
        await event_bus.publish(
            topic="task.queued",
            sender="TaskQueue",
            payload={"task_id": task_id, "execution_id": execution_id}
        )

        logger.info(f"Enqueued task {task_id} for execution {execution_id} (Redis={redis is not None})")
        return task_id

    @staticmethod
    async def get_status(task_id: str) -> Dict[str, str]:
        redis = db_manager.redis_client
        if redis:
            return await redis.hgetall(f"task:status:{task_id}")
        return _in_memory_task_statuses.get(task_id, {})


class WorkerPool:
    def __init__(self, agent_manager: Any):
        self.agent_manager = agent_manager
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def start(self, num_workers: int = 3) -> None:
        if self._running:
            return
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker_loop(worker_id=i))
            self._workers.append(task)
        logger.info(f"Worker Pool started with {num_workers} workers.")

    async def stop(self) -> None:
        self._running = False
        for task in self._workers:
            task.cancel()
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
            self._workers.clear()
        logger.info("Worker Pool stopped.")

    async def _worker_loop(self, worker_id: int) -> None:
        logger.info(f"Worker-{worker_id} entering execution queue loop...")
        while self._running:
            try:
                redis = db_manager.redis_client
                payload_str = None

                if redis:
                    result = await redis.blpop("queue:tasks", timeout=1)
                    if result:
                        _, payload_str = result
                else:
                    try:
                        qsize = _in_memory_task_queue.qsize()
                        qid = id(_in_memory_task_queue)
                        logger.info(f"Worker-{worker_id}: polling, queue.id={qid} qsize={qsize}")
                        payload_str = await asyncio.wait_for(_in_memory_task_queue.get(), timeout=1.0)
                        logger.info(f"Worker-{worker_id}: GOT payload! len={len(payload_str)}")
                    except asyncio.TimeoutError:
                        pass

                if not payload_str:
                    continue

                payload = json.loads(payload_str)
                task_id = payload["task_id"]
                execution_id = payload["execution_id"]
                step_data = payload["step_data"]

                logger.info(f"Worker-{worker_id} picked up task {task_id}")
                await self._execute_task(worker_id, task_id, execution_id, step_data)

            except asyncio.CancelledError:
                # Don't break — log and continue the loop so the worker
                # can process future tasks after a cancellation.
                logger.warning(f"Worker-{worker_id}: CancelledError caught, continuing loop")
                continue
            except Exception as e:
                logger.error(f"Worker-{worker_id} encountered queue read error: {e}")
                await asyncio.sleep(2)

    async def _execute_task(
        self, worker_id: int, task_id: str, execution_id: str, step_data: Dict[str, Any]
    ) -> None:
        redis = db_manager.redis_client
        
        if redis:
            await redis.hset(f"task:status:{task_id}", "status", "running")
        else:
            if task_id in _in_memory_task_statuses:
                _in_memory_task_statuses[task_id]["status"] = "running"

        await event_bus.publish(
            topic="task.started",
            sender=f"Worker-{worker_id}",
            payload={"task_id": task_id, "execution_id": execution_id}
        )

        try:
            async def progress_callback(percentage: int, logs: str):
                if redis:
                    await redis.hset(
                        f"task:status:{task_id}",
                        mapping={"progress": str(percentage), "logs": logs}
                    )
                else:
                    if task_id in _in_memory_task_statuses:
                        _in_memory_task_statuses[task_id]["progress"] = str(percentage)
                        _in_memory_task_statuses[task_id]["logs"] = logs

                await event_bus.publish(
                    topic="task.progress",
                    sender=f"Worker-{worker_id}",
                    payload={
                        "task_id": task_id,
                        "execution_id": execution_id,
                        "progress": percentage,
                        "logs": logs
                    }
                )

            logger.info(f"Worker-{worker_id}: About to execute step {step_data}")

            # Check cancellation before running
            try:
                from app.services.state_machine import WorkflowStateMachine, WorkflowState
                exec_status = await WorkflowStateMachine.get_status(execution_id)
                if exec_status == WorkflowState.CANCELLED.value:
                    logger.info(f"Worker-{worker_id}: execution {execution_id} is cancelled, skipping task {task_id}")
                    return
            except Exception:
                pass

            # Wrap execution with periodic cancellation checks
            async def _checked_execute():
                """Execute step with periodic cancellation checks."""
                from app.services.state_machine import WorkflowStateMachine, WorkflowState
                result = [None]
                check_interval = 0.5  # Check every 0.5 seconds for faster cancellation
                step_task = asyncio.create_task(
                    self.agent_manager.execute_step(step_data, progress_callback,
                                                    user_id=step_data.get("user_id"),
                                                    execution_id=execution_id)
                )
                check_task = asyncio.create_task(_periodic_cancel_check(execution_id, check_interval))
                try:
                    done, pending = await asyncio.wait(
                        {step_task, check_task},
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    # Cancel whichever is still running
                    for t in pending:
                        t.cancel()
                        try:
                            await t
                        except (asyncio.CancelledError, Exception):
                            pass
                    # If the step task completed, return its result
                    if step_task in done:
                        result[0] = step_task.result()
                    else:
                        # Check was cancelled — kill the process and raise
                        from app.services.process_manager import cancel_process
                        cancel_process(execution_id)
                        raise asyncio.CancelledError("Workflow cancelled")
                    return result[0]
                except asyncio.CancelledError:
                    step_task.cancel()
                    check_task.cancel()
                    from app.services.process_manager import cancel_process
                    cancel_process(execution_id)
                    raise

            async def _periodic_cancel_check(eid: str, interval: float):
                """Periodically check if the execution was cancelled or stopping."""
                from app.services.state_machine import WorkflowStateMachine, WorkflowState
                while True:
                    await asyncio.sleep(interval)
                    try:
                        status = await WorkflowStateMachine.get_status(eid)
                        if status in (WorkflowState.CANCELLED.value, WorkflowState.STOPPING.value):
                            # Kill the process tree
                            from app.services.process_manager import cancel_process
                            cancel_process(eid)
                            # If STOPPING, transition to CANCELLED
                            if status == WorkflowState.STOPPING.value:
                                await WorkflowStateMachine.transition_to(eid, WorkflowState.CANCELLED)
                            return
                    except Exception:
                        pass

            try:
                result = await asyncio.wait_for(
                    _checked_execute(),
                    timeout=TASK_EXECUTION_TIMEOUT,
                )
            except asyncio.TimeoutError:
                error_msg = f"Task execution timed out after {TASK_EXECUTION_TIMEOUT}s"
                logger.error(f"Worker-{worker_id}: {error_msg} for task {task_id}")
                failed_mapping = {"status": "failed", "error": error_msg}
                if redis:
                    await redis.hset(f"task:status:{task_id}", mapping=failed_mapping)
                else:
                    if task_id in _in_memory_task_statuses:
                        _in_memory_task_statuses[task_id].update(failed_mapping)
                await event_bus.publish(
                    topic="task.failed",
                    sender=f"Worker-{worker_id}",
                    payload={"task_id": task_id, "execution_id": execution_id, "error": error_msg, "step_data": step_data},
                )
                return
            logger.info(f"Worker-{worker_id}: Step executed OK. Result={result}")

            # --- Verification Phase ---
            vresult = await verification_engine.verify(step_data, result)
            logger.info(f"Worker-{worker_id}: Verification {'PASSED' if vresult.success else 'FAILED'} [{vresult.message}]")

            if vresult.success:
                completed_mapping = {
                    "status": "completed",
                    "progress": "100",
                    "result": json.dumps(result),
                    "verification": json.dumps({
                        "success": True,
                        "message": vresult.message,
                        "confidence": vresult.confidence,
                        "diagnostics": vresult.diagnostics,
                    }),
                }
                if redis:
                    await redis.hset(f"task:status:{task_id}", mapping=completed_mapping)
                else:
                    if task_id in _in_memory_task_statuses:
                        _in_memory_task_statuses[task_id].update(completed_mapping)

                await event_bus.publish(
                    topic="task.completed",
                    sender=f"Worker-{worker_id}",
                    payload={
                        "task_id": task_id,
                        "execution_id": execution_id,
                        "result": result,
                        "verification": {
                            "success": True,
                            "message": vresult.message,
                            "confidence": vresult.confidence,
                            "diagnostics": vresult.diagnostics,
                        },
                    }
                )
                logger.info(f"Worker-{worker_id}: Published task.completed for task {task_id}, execution {execution_id}")
            else:
                await event_bus.publish(
                    topic="verification.failed",
                    sender=f"Worker-{worker_id}",
                    payload={
                        "task_id": task_id,
                        "execution_id": execution_id,
                        "result": result,
                        "step_data": step_data,
                        "verification": {
                            "success": False,
                            "message": vresult.message,
                            "confidence": vresult.confidence,
                            "diagnostics": vresult.diagnostics,
                        },
                    }
                )
                logger.info(f"Worker-{worker_id}: Published verification.failed for task {task_id}, execution {execution_id}")
            logger.info(f"Worker-{worker_id} successfully completed task {task_id}")
            _cleanup_task_statuses()

        except Exception as e:
            tb = traceback.format_exc()
            error_msg = str(e) or type(e).__name__ or "Unknown error"
            error_type = type(e).__name__
            logger.error(f"Worker-{worker_id} failed task {task_id}: {error_msg}\n{tb}")

            # Build structured error details for the frontend
            error_details = {
                "message": error_msg,
                "type": error_type,
                "agent_type": step_data.get("agent_type", "unknown"),
                "action": step_data.get("action", "unknown"),
                "step_name": step_data.get("name", ""),
                "step_id": step_data.get("step_id", ""),
                "suggestion": _get_error_suggestion(error_type, error_msg, step_data),
            }
            
            failed_mapping = {
                "status": "failed",
                "error": error_msg,
                "error_details": json.dumps(error_details),
            }
            if redis:
                await redis.hset(f"task:status:{task_id}", mapping=failed_mapping)
            else:
                if task_id in _in_memory_task_statuses:
                    _in_memory_task_statuses[task_id].update(failed_mapping)

            await event_bus.publish(
                topic="task.failed",
                sender=f"Worker-{worker_id}",
                payload={
                    "task_id": task_id,
                    "execution_id": execution_id,
                    "error": error_msg,
                    "error_details": error_details,
                    "step_data": step_data,
                }
            )