from fastapi import APIRouter, HTTPException, Depends
from typing import List
from bson import ObjectId

from app.core.database import db_manager
from app.infrastructure.db.models import WorkflowExecution, TaskLog, User
from app.infrastructure.memory_db import memory_db
from app.services.workflow_engine import workflow_engine
from app.api.deps import get_current_user, get_user_id

router = APIRouter()


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
        return {
            "_id": str(execution.id),
            "workflow_id": str(execution.workflow_id),
            "user_id": str(execution.user_id),
            "title": execution.title or "",
            "description": execution.description or "",
            "status": execution.status,
            "current_step_index": execution.current_step_index,
            "total_steps": execution.total_steps,
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "error_message": execution.error_message,
            "result": execution.result,
        }


@router.get("")
async def list_executions(user: User = Depends(get_current_user)):
    user_id = get_user_id(user)
    if db_manager.use_memory:
        all_docs = await memory_db.find_sorted("workflow_executions", "created_at", limit=100)
        return [d for d in all_docs if d.get("user_id") == user_id]
    executions = await WorkflowExecution.find(WorkflowExecution.user_id == user.id).sort(-WorkflowExecution.started_at).to_list()
    return [
        {
            "_id": str(ex.id),
            "workflow_id": str(ex.workflow_id),
            "title": ex.title or "",
            "description": ex.description or "",
            "status": ex.status,
            "current_step_index": ex.current_step_index,
            "total_steps": ex.total_steps,
            "started_at": ex.started_at.isoformat() if ex.started_at else None,
            "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
            "error_message": ex.error_message,
            "result": ex.result,
        }
        for ex in executions
    ]


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

    if db_manager.use_memory:
        await memory_db.update("workflow_executions", {"_id": ObjectId(id)}, {"status": "Cancelled"})
        return {"success": True, "status": "Cancelled"}
    execution = await WorkflowExecution.get(ObjectId(id))
    if not execution:
        raise HTTPException(status_code=404, detail="Workflow execution not found")
    try:
        await workflow_engine.abort_execution(id)
        return {"success": True, "status": "aborting"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
