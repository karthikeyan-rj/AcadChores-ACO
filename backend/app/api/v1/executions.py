from fastapi import APIRouter, HTTPException, Depends
from typing import List
from bson import ObjectId

from app.core.database import db_manager
from app.infrastructure.db.models import WorkflowExecution, TaskLog, User
from app.infrastructure.memory_db import memory_db
from app.services.workflow_engine import workflow_engine
from app.services.process_manager import cancel_process
from app.api.deps import get_current_user, get_user_id

router = APIRouter()


def map_display_status(status: str, result_type: str = None) -> str:
    """Map internal workflow status to user-facing display status.

    Only three display statuses are allowed: completed, stopped, draft.
    """
    s = (status or "").lower()
    if s == "completed":
        return "completed"
    if s in ("cancelled", "stopped"):
        return "stopped"
    if s == "failed":
        if result_type == "failed":
            return "stopped"
        return "stopped"
    if s in ("idle", "draft"):
        return "draft"
    if s in ("planning", "awaiting_approval"):
        return "draft"
    if s in ("executing", "running", "waiting", "retry", "stopping", "queued"):
        return None
    return None


def _execution_to_history_dict(ex, source: str = "beanie") -> dict:
    """Convert an execution document to a History API response dict."""
    if source == "beanie":
        doc = {
            "_id": str(ex.id),
            "workflow_id": str(ex.workflow_id),
            "conversation_id": getattr(ex, "conversation_id", None),
            "title": ex.title or "",
            "description": ex.description or "",
            "status": ex.status,
            "current_step_index": ex.current_step_index,
            "total_steps": ex.total_steps,
            "started_at": ex.started_at.isoformat() if hasattr(ex, "started_at") and ex.started_at else None,
            "completed_at": ex.completed_at.isoformat() if hasattr(ex, "completed_at") and ex.completed_at else None,
            "stopped_at": getattr(ex, "stopped_at", None),
            "error_message": ex.error_message,
            "result": ex.result,
            "result_type": getattr(ex, "result_type", None),
            "created_at": ex.created_at.isoformat() if hasattr(ex, "created_at") and ex.created_at else None,
        }
    else:
        doc = {
            "_id": str(ex.get("_id", "")),
            "workflow_id": str(ex.get("workflow_id", "")),
            "conversation_id": ex.get("conversation_id"),
            "title": ex.get("title", ""),
            "description": ex.get("description", ""),
            "status": ex.get("status", ""),
            "current_step_index": ex.get("current_step_index", 0),
            "total_steps": ex.get("total_steps", 0),
            "started_at": ex.get("started_at"),
            "completed_at": ex.get("completed_at"),
            "stopped_at": ex.get("stopped_at"),
            "error_message": ex.get("error_message"),
            "result": ex.get("result"),
            "result_type": ex.get("result_type"),
            "created_at": ex.get("created_at"),
        }

    display = map_display_status(doc["status"], doc.get("result_type"))
    doc["display_status"] = display

    if doc["started_at"] and (doc.get("completed_at") or doc.get("stopped_at")):
        from datetime import datetime, timezone
        end = doc.get("completed_at") or doc.get("stopped_at")
        try:
            start_dt = datetime.fromisoformat(doc["started_at"].replace("Z", "+00:00"))
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=timezone.utc)
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            doc["duration_ms"] = int((end_dt - start_dt).total_seconds() * 1000)
        except (ValueError, TypeError):
            doc["duration_ms"] = None
    else:
        doc["duration_ms"] = None

    return doc


async def _verify_execution_owner(execution_id: str, user_id: str) -> dict:
    """Find execution and verify it belongs to the authenticated user. Raises 404/403."""
    if db_manager.use_memory:
        doc = await memory_db.find_one("workflow_executions", {"_id": ObjectId(execution_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Execution not found")
        if str(doc.get("user_id", "")) != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return doc
    else:
        execution = await WorkflowExecution.get(ObjectId(execution_id))
        if not execution:
            raise HTTPException(status_code=404, detail="Workflow execution not found")
        if str(execution.user_id) != user_id:
            raise HTTPException(status_code=403, detail="Access denied")
        return _execution_to_history_dict(execution, "beanie")


@router.get("")
async def list_executions(user: User = Depends(get_current_user)):
    user_id = get_user_id(user)
    if db_manager.use_memory:
        all_docs = await memory_db.find_sorted("workflow_executions", "created_at", limit=200)
        user_docs = [d for d in all_docs if d.get("user_id") == user_id]
        result = [_execution_to_history_dict(d, "memory") for d in user_docs]
    else:
        executions = await WorkflowExecution.find(
            WorkflowExecution.user_id == user.id
        ).sort(-WorkflowExecution.started_at).to_list(200)
        result = [_execution_to_history_dict(ex, "beanie") for ex in executions]

    return result


@router.get("/{id}")
async def get_execution(id: str, user: User = Depends(get_current_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    return await _verify_execution_owner(id, get_user_id(user))


@router.get("/{id}/logs")
async def get_execution_logs(id: str, user: User = Depends(get_current_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    await _verify_execution_owner(id, get_user_id(user))

    if db_manager.use_memory:
        docs = await memory_db.find("task_logs", {"execution_id": str(ObjectId(id))})
        return docs
    logs = await TaskLog.find(TaskLog.execution_id == ObjectId(id)).to_list()
    return [
        {
            "step_id": log.step_id,
            "agent_name": log.agent_name,
            "action": log.action,
            "status": log.status,
            "logs": log.logs,
            "created_at": log.created_at
        }
        for log in logs
    ]


@router.post("/{id}/abort")
async def abort_execution(id: str, user: User = Depends(get_current_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")
    await _verify_execution_owner(id, get_user_id(user))

    cancel_process(id)

    try:
        await workflow_engine.abort_execution(id)
        return {"success": True, "status": "Stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
