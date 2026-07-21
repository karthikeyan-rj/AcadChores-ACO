import logging
import asyncio
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from bson import ObjectId

from app.core.database import db_manager
from app.infrastructure.memory_db import memory_db
from app.core.event_bus import event_bus, SystemEvent
from app.services.state_machine import WorkflowStateMachine, WorkflowState
from app.services.worker import TaskQueue
from app.infrastructure.db.models import Workflow, WorkflowExecution, TaskLog, Step, ChatMessage
from app.recovery import recovery_engine, RecoveryStrategy
from app.verification import verification_engine
from app.ai.capabilities import capability_registry

logger = logging.getLogger(__name__)


def _exec_to_dict(exec_doc) -> Optional[dict]:
    """Normalize an execution doc (dict or Beanie model) to a plain dict."""
    if exec_doc is None:
        return None
    if isinstance(exec_doc, dict):
        return exec_doc
    return {
        "id": str(exec_doc.id),
        "workflow_id": str(exec_doc.workflow_id),
        "user_id": str(exec_doc.user_id) if exec_doc.user_id else "",
        "status": exec_doc.status,
        "current_step_index": exec_doc.current_step_index,
        "started_at": exec_doc.started_at.isoformat() if hasattr(exec_doc.started_at, 'isoformat') else str(exec_doc.started_at) if exec_doc.started_at else None,
        "completed_at": exec_doc.completed_at.isoformat() if hasattr(exec_doc.completed_at, 'isoformat') else str(exec_doc.completed_at) if exec_doc.completed_at else None,
        "error_message": exec_doc.error_message,
    }


async def _find_exec(execution_id: str) -> Optional[dict]:
    """Find an execution by ID, trying memory_db first then MongoDB, returning a dict."""
    doc = await memory_db.find_one("workflow_executions", {"_id": ObjectId(execution_id)})
    if doc:
        return doc
    if not db_manager.use_memory:
        try:
            model = await WorkflowExecution.get(ObjectId(execution_id))
            return _exec_to_dict(model)
        except Exception:
            pass
    return None


async def _find_workflow(wid) -> Optional[Any]:
    """Find a workflow by ID, returning the raw object (dict or model)."""
    if db_manager.use_memory:
        return await memory_db.find_one("workflows", {"_id": ObjectId(str(wid))})
    else:
        try:
            return await Workflow.get(ObjectId(str(wid)))
        except Exception:
            return None


def _get_steps(workflow) -> list:
    """Extract steps list from a workflow (dict or model)."""
    if isinstance(workflow, dict):
        return workflow.get("steps", [])
    return workflow.steps if workflow else []


def _get_step_attr(step, attr: str, default=None):
    """Get an attribute from a step (dict or model)."""
    if isinstance(step, dict):
        return step.get(attr, default)
    return getattr(step, attr, default)


class WorkflowEngine:
    def __init__(self):
        event_bus.subscribe("task.completed", self._handle_step_completed)
        event_bus.subscribe("task.failed", self._handle_step_failed)
        event_bus.subscribe("verification.failed", self._handle_verification_failed)
        event_bus.subscribe("workflow.state_change", self._handle_state_change)

    async def start_execution(self, workflow, user_id, conversation_id: Optional[str] = None) -> str:
        if not (isinstance(workflow, dict) or hasattr(workflow, 'id')):
            workflow_obj = await Workflow.get(workflow)
            if not workflow_obj:
                raise ValueError(f"Workflow not found: {workflow}")
            workflow = workflow_obj

        wf_title = workflow.title if hasattr(workflow, 'title') else (workflow.get("title", "") if isinstance(workflow, dict) else "")
        wf_desc = workflow.description if hasattr(workflow, 'description') else (workflow.get("description", "") if isinstance(workflow, dict) else "")
        steps_list = _get_steps(workflow)
        steps_dicts = []
        for s in steps_list:
            if hasattr(s, 'model_dump'):
                steps_dicts.append(s.model_dump())
            elif isinstance(s, dict):
                steps_dicts.append(s)
            else:
                steps_dicts.append({"step_id": str(getattr(s, 'step_id', '')), "name": str(getattr(s, 'name', '')), "agent_type": str(getattr(s, 'agent_type', '')), "action": str(getattr(s, 'action', ''))})
        total_steps = len(steps_list)

        now = datetime.now(timezone.utc)
        if db_manager.use_memory:
            exec_doc = {
                "workflow_id": str(workflow.id),
                "user_id": str(user_id),
                "conversation_id": conversation_id,
                "title": wf_title,
                "description": wf_desc,
                "steps": steps_dicts,
                "status": WorkflowState.IDLE.value,
                "current_step_index": 0,
                "total_steps": total_steps,
                "started_at": now.isoformat(),
                "completed_at": None,
                "stopped_at": None,
                "error_message": None,
                "result": None,
                "result_type": None,
                "last_completed_step": None,
                "partial_result": None,
                "created_at": now.isoformat()
            }
            oid = await memory_db.insert("workflow_executions", exec_doc)
            execution_id = str(oid)
        else:
            execution = WorkflowExecution(
                workflow_id=workflow.id,
                user_id=user_id,
                conversation_id=conversation_id,
                title=wf_title,
                description=wf_desc,
                steps=steps_dicts,
                status=WorkflowState.IDLE.value,
                current_step_index=0,
                total_steps=total_steps,
                started_at=now,
                completed_at=None,
                stopped_at=None,
                error_message=None,
                result=None,
                result_type=None,
                last_completed_step=None,
                partial_result=None,
            )
            await execution.insert()
            execution_id = str(execution.id)

        await WorkflowStateMachine.transition_to(execution_id, WorkflowState.PLANNING)
        await WorkflowStateMachine.transition_to(execution_id, WorkflowState.EXECUTING)
        try:
            await self._dispatch_next_step(execution_id, workflow)
        except Exception as e:
            err_msg = str(e) or type(e).__name__ or "Unknown error in start_execution"
            logger.error(f"start_execution failed: {err_msg}\n{traceback.format_exc()}")
            await WorkflowStateMachine.transition_to(execution_id, WorkflowState.FAILED, error_message=err_msg)
        return execution_id

    async def abort_execution(self, execution_id: str) -> None:
        await WorkflowStateMachine.transition_to(execution_id, WorkflowState.STOPPING)
        logger.info(f"Execution {execution_id} requested cancellation (STOPPING).")
        # The worker's _periodic_cancel_check will observe STOPPING,
        # kill the process tree, and transition to CANCELLED.

    async def _dispatch_next_step(self, execution_id: str, workflow=None) -> None:
        exec_doc = await _find_exec(execution_id)
        if not exec_doc:
            logger.warning(f"_dispatch_next_step: execution {execution_id} not found")
            return

        if exec_doc.get("status") == WorkflowState.CANCELLED.value:
            return

        if workflow is None:
            wid = exec_doc.get("workflow_id", "")
            workflow = await _find_workflow(wid)
        if not workflow:
            logger.warning(f"_dispatch_next_step: workflow not found for execution {execution_id}")
            return

        user_id = str(exec_doc.get("user_id", ""))
        step_idx = exec_doc.get("current_step_index", 0)
        steps = _get_steps(workflow)
        logger.info(f"[WorkflowEngine] _dispatch_next_step: execution={execution_id}, step_idx={step_idx}/{len(steps)}")

        if step_idx >= len(steps):
            await WorkflowStateMachine.transition_to(execution_id, WorkflowState.COMPLETED)
            return

        step_data = steps[step_idx]
        if hasattr(step_data, 'model_dump'):
            step_payload = step_data.model_dump()
        else:
            step_payload = step_data

        step_payload["user_id"] = user_id

        try:
            await TaskQueue.enqueue(execution_id, step_payload)
        except Exception as e:
            logger.error(f"enqueue failed: {e}\n{traceback.format_exc()}")
            return
        logger.info(f"Dispatched step index {step_idx} for execution {execution_id} (user={user_id})")

    async def _handle_step_completed(self, event: SystemEvent) -> None:
        payload = event.payload
        execution_id = payload.get("execution_id")
        result = payload.get("result", {})
        logger.info(f"[WorkflowEngine] task.completed received for execution={execution_id}")

        try:
            exec_doc = await _find_exec(execution_id)
            if not exec_doc or exec_doc.get("status") != WorkflowState.EXECUTING.value:
                logger.warning(f"[WorkflowEngine] Step completed but exec not found or not EXECUTING: exec_doc={exec_doc is not None}, status={exec_doc.get('status') if exec_doc else 'N/A'}")
                return

            wid = exec_doc.get("workflow_id", "")
            workflow_doc = await _find_workflow(wid)
            if not workflow_doc:
                logger.error(f"[WorkflowEngine] Workflow {wid} not found for execution {execution_id}")
                return

            step_idx = exec_doc.get("current_step_index", 0)
            steps_list = _get_steps(workflow_doc)
            step = steps_list[step_idx] if step_idx < len(steps_list) else {}
            logger.info(f"[WorkflowEngine] Processing step_idx={step_idx}/{len(steps_list)}, step_id={_get_step_attr(step, 'step_id')}")

            # Extract a readable result string from the step result
            result_text = ""
            if result:
                if isinstance(result, dict):
                    if result.get("links"):
                        links = result["links"]
                        result_text = "\n".join(f"{i+1}. {l.get('title', '')} → {l.get('url', '')}" for i, l in enumerate(links))
                    elif result.get("summary"):
                        result_text = result["summary"]
                    elif result.get("text"):
                        result_text = result["text"]
                    elif result.get("stdout"):
                        result_text = result["stdout"]
                    elif result.get("content"):
                        result_text = result["content"]
                    else:
                        result_text = str(result)
                else:
                    result_text = str(result)

            if db_manager.use_memory:
                await memory_db.insert("task_logs", {
                    "execution_id": execution_id,
                    "user_id": str(exec_doc.get("user_id", "")),
                    "step_id": _get_step_attr(step, "step_id"),
                    "agent_name": _get_step_attr(step, "agent_type"),
                    "action": _get_step_attr(step, "action"),
                    "status": "success",
                    "logs": f"Step completed successfully. Result details: {result}"
                })
                step_name = _get_step_attr(step, "name", "")
                update_fields = {
                    "current_step_index": step_idx + 1,
                    "last_completed_step": f"Step {step_idx + 1} — {step_name}" if step_name else f"Step {step_idx + 1}",
                }
                if result_text:
                    update_fields["result"] = result_text
                    update_fields["partial_result"] = result_text
                update_ok = await memory_db.update("workflow_executions", {"_id": ObjectId(execution_id)}, update_fields)
                logger.info(f"[WorkflowEngine] memory_db update result={update_ok}, new_step_index={step_idx + 1}, exec_id={execution_id}")
            else:
                log_entry = TaskLog(
                    execution_id=ObjectId(execution_id),
                    user_id=ObjectId(str(exec_doc.get("user_id", ""))) if exec_doc.get("user_id") else None,
                    step_id=_get_step_attr(step, "step_id"),
                    agent_name=_get_step_attr(step, "agent_type"),
                    action=_get_step_attr(step, "action"),
                    status="success",
                    logs=f"Step completed successfully. Result details: {result}"
                )
                await log_entry.insert()
                exec_model = await WorkflowExecution.get(ObjectId(execution_id))
                if exec_model:
                    exec_model.current_step_index += 1
                    step_name = _get_step_attr(step, "name", "")
                    exec_model.last_completed_step = f"Step {step_idx + 1} — {step_name}" if step_name else f"Step {step_idx + 1}"
                    if result_text:
                        exec_model.result = result_text
                        exec_model.partial_result = result_text
                    await exec_model.save()

            logger.info(f"[WorkflowEngine] Step {step_idx} completed. Dispatching next step...")
            await self._dispatch_next_step(execution_id, workflow_doc)
            logger.info(f"[WorkflowEngine] Next step dispatched successfully for execution {execution_id}")
        except Exception as e:
            logger.error(f"[WorkflowEngine] Error in _handle_step_completed for {execution_id}: {e}\n{traceback.format_exc()}")

    async def _handle_verification_failed(self, event: SystemEvent) -> None:
        payload = event.payload
        execution_id = payload.get("execution_id")
        step_data = payload.get("step_data", {})
        result = payload.get("result", {})
        verification = payload.get("verification", {})

        exec_doc = await _find_exec(execution_id)
        if not exec_doc or exec_doc.get("status") not in (WorkflowState.EXECUTING.value, WorkflowState.RETRY.value):
            return

        # Prevent recovery after cancellation
        if exec_doc.get("status") == WorkflowState.CANCELLED.value:
            return

        step_id = step_data.get("step_id", "")
        recovery_action = await recovery_engine.recover(
            step=step_data,
            error=None,
            verification_result=verification,
            step_id=step_id,
        )

        logger.info(f"Recovery decision for {step_id}: {recovery_action.strategy.value} — {recovery_action.message}")

        if recovery_action.strategy == RecoveryStrategy.ABORT:
            error_msg = recovery_action.message or f"Verification failed after recovery: {verification.get('message', '')}"
            step_name = step_data.get("name", step_data.get("action", ""))
            agent_type = step_data.get("agent_type", "unknown")
            action = step_data.get("action", "unknown")
            abort_details = {
                "message": error_msg,
                "type": "VerificationError",
                "agent_type": agent_type,
                "action": action,
                "step_name": step_name,
                "step_id": step_id,
                "suggestion": f"Step '{step_name}' failed verification. The {agent_type}/{action} action did not produce the expected result.",
            }
            await self._log_failure(execution_id, step_data, error_msg)
            await WorkflowStateMachine.transition_to(
                execution_id, WorkflowState.FAILED, error_message=error_msg,
                metadata={"error_details": abort_details},
            )
            return

        if recovery_action.delay_seconds > 0:
            await asyncio.sleep(recovery_action.delay_seconds)
        else:
            await asyncio.sleep(0.5)

        modified_step = recovery_action.modified_step or step_data
        modified_step["user_id"] = str(exec_doc.get("user_id", ""))
        modified_step["_recovery_attempt"] = recovery_engine.get_attempts(step_id)
        modified_step["_recovery_strategy"] = recovery_action.strategy.value

        try:
            await TaskQueue.enqueue(execution_id, modified_step)
            logger.info(f"Recovery re-enqueued step {step_id} using {recovery_action.strategy.value}")
        except Exception as e:
            logger.error(f"Recovery enqueue failed: {e}")
            await WorkflowStateMachine.transition_to(execution_id, WorkflowState.FAILED, error_message=str(e))

    async def _handle_step_failed(self, event: SystemEvent) -> None:
        payload = event.payload
        execution_id = payload.get("execution_id")
        error_msg = payload.get("error", "Unknown error")
        step_data = payload.get("step_data", {})
        error_details = payload.get("error_details", {})

        exec_doc = await _find_exec(execution_id)
        if not exec_doc or exec_doc.get("status") not in (WorkflowState.EXECUTING.value, WorkflowState.RETRY.value):
            return

        # Prevent recovery after cancellation
        if exec_doc.get("status") == WorkflowState.CANCELLED.value:
            return

        # Try recovery before failing
        step_id = step_data.get("step_id", "")
        recovery_action = await recovery_engine.recover(
            step=step_data,
            error=Exception(error_msg) if error_msg else None,
            verification_result=None,
            step_id=step_id,
        )

        if recovery_action.strategy != RecoveryStrategy.ABORT:
            if recovery_action.delay_seconds > 0:
                await asyncio.sleep(recovery_action.delay_seconds)
            else:
                await asyncio.sleep(0.5)
            modified_step = recovery_action.modified_step or step_data
            modified_step["user_id"] = str(exec_doc.get("user_id", ""))
            modified_step["_recovery_attempt"] = recovery_engine.get_attempts(step_id)
            try:
                await TaskQueue.enqueue(execution_id, modified_step)
                logger.info(f"Recovery from failure: re-enqueued step {step_id} using {recovery_action.strategy.value}")
                return
            except Exception:
                pass

        # Log failure and transition to FAILED
        wid = exec_doc.get("workflow_id", "")
        workflow_doc = await _find_workflow(wid)
        step_idx = exec_doc.get("current_step_index", 0)
        steps_list = _get_steps(workflow_doc)
        step = steps_list[step_idx] if steps_list else {}

        if db_manager.use_memory:
            await memory_db.insert("task_logs", {
                "execution_id": execution_id,
                "user_id": str(exec_doc.get("user_id", "")),
                "step_id": _get_step_attr(step, "step_id"),
                "agent_name": _get_step_attr(step, "agent_type"),
                "action": _get_step_attr(step, "action"),
                "status": "failure",
                "logs": f"Step execution failed: {error_msg}"
            })
        else:
            log_entry = TaskLog(
                execution_id=ObjectId(execution_id),
                user_id=ObjectId(str(exec_doc.get("user_id", ""))) if exec_doc.get("user_id") else None,
                step_id=_get_step_attr(step, "step_id"),
                agent_name=_get_step_attr(step, "agent_type"),
                action=_get_step_attr(step, "action"),
                status="failure",
                logs=f"Step execution failed: {error_msg}"
            )
            await log_entry.insert()

        await WorkflowStateMachine.transition_to(
            execution_id, WorkflowState.FAILED, error_message=error_msg,
            metadata={"error_details": error_details} if error_details else None,
        )
        logger.error(f"Workflow execution {execution_id} halted on step failure: {error_msg}")

    async def _handle_state_change(self, event: SystemEvent) -> None:
        """Save a conversation message when a workflow reaches a terminal state.

        Idempotent: checks for an existing message with the same execution_id
        and workflow_state before inserting, so reconnects or repeated events
        cannot create duplicate completion or stopped messages.
        """
        payload = event.payload
        new_state = payload.get("new_state", "")
        if new_state not in ("Completed", "Failed", "Cancelled"):
            return

        execution_id = payload.get("execution_id", "")
        exec_doc = await _find_exec(execution_id)
        if not exec_doc:
            return

        conversation_id = exec_doc.get("conversation_id")
        user_id = exec_doc.get("user_id")
        if not conversation_id or not user_id:
            return

        # Idempotency check: skip if a message for this execution_id + state already exists
        if db_manager.use_memory:
            existing = await memory_db.find("chat_messages", {
                "user_id": str(user_id),
                "conversation_id": conversation_id,
                "execution_id": execution_id,
                "metadata.workflow_state": new_state,
            })
            if existing:
                logger.info(f"Skipping duplicate {new_state} message for execution {execution_id}")
                return
        else:
            existing = await ChatMessage.find(
                ChatMessage.user_id == user_id,
                ChatMessage.conversation_id == conversation_id,
                ChatMessage.execution_id == execution_id,
            ).to_list()
            for msg in existing:
                if (msg.metadata or {}).get("workflow_state") == new_state:
                    logger.info(f"Skipping duplicate {new_state} message for execution {execution_id}")
                    return

        title = exec_doc.get("title", "Task")
        last_step = exec_doc.get("last_completed_step", "")
        error_msg = exec_doc.get("error_message", "")
        result_text = exec_doc.get("result", "") or exec_doc.get("partial_result", "")

        if new_state == "Completed":
            content = f"Workflow completed: {title}"
            if result_text:
                content += f"\n\nResult:\n{result_text}"
            message_type = "assistant"
        elif new_state == "Failed":
            content = f"Workflow failed: {title}"
            if error_msg:
                content += f"\n\nError: {error_msg}"
            if last_step:
                content += f"\n\nLast step: {last_step}"
            message_type = "error"
        elif new_state == "Cancelled":
            content = f"Workflow stopped: {title}"
            if last_step:
                content += f"\n\nStopped during: {last_step}"
            else:
                content += "\n\nThe task was stopped by the user."
            message_type = "assistant"
        else:
            return

        try:
            msg = ChatMessage(
                user_id=user_id,
                conversation_id=conversation_id,
                role="assistant",
                message_type=message_type,
                content=content,
                execution_id=execution_id,
                metadata={"workflow_state": new_state, "execution_id": execution_id},
            )
            await msg.insert()
            logger.info(f"Saved {new_state} message for execution {execution_id} in conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to save workflow result message: {e}")


workflow_engine = WorkflowEngine()
