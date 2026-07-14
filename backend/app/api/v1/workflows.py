from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pydantic import BaseModel
from beanie import PydanticObjectId

from app.core.database import db_manager
from app.core.config import settings
from app.core.rate_limit import limiter
from app.infrastructure.db.models import Workflow, Step, User
from app.infrastructure.memory_db import memory_db
from app.services.planner import planner_service
from app.services.workflow_engine import workflow_engine
from app.api.deps import get_current_user, get_user_id

router = APIRouter()

class CreateWorkflowRequest(BaseModel):
    title: str
    description: str
    steps: List[Step]

class PlanGenerationRequest(BaseModel):
    prompt: str

class ChatRequest(BaseModel):
    message: str

class PlanGenerationResponse(BaseModel):
    success: bool
    steps: List[Dict[str, Any]]
    planner_metadata: Optional[Dict[str, Any]] = None

@router.get("")
async def list_workflows(user: User = Depends(get_current_user)):
    if db_manager.use_memory:
        all_docs = await memory_db.find_sorted("workflows", "created_at", limit=200)
        return [d for d in all_docs if d.get("owner_id") == get_user_id(user)]
    workflows = await Workflow.find(Workflow.owner_id == user.id).to_list()
    return workflows

@router.post("")
async def create_workflow(req: CreateWorkflowRequest, user: User = Depends(get_current_user)):
    if db_manager.use_memory:
        steps_dicts = [s.model_dump() if hasattr(s, 'model_dump') else s for s in req.steps]
        doc = {
            "title": req.title,
            "description": req.description,
            "owner_id": str(user.id),
            "steps": steps_dicts,
            "created_at": __import__('datetime').datetime.utcnow().isoformat()
        }
        oid = await memory_db.insert("workflows", doc)
        return {"_id": str(oid), "title": req.title, "steps": steps_dicts}
    workflow = Workflow(
        title=req.title,
        description=req.description,
        owner_id=user.id,
        steps=[Step(**s) if isinstance(s, dict) else s for s in req.steps]
    )
    await workflow.insert()
    return {"_id": str(workflow.id), "title": workflow.title, "steps": [s.model_dump() for s in workflow.steps]}

@router.post("/generate-plan")
@limiter.limit(settings.RATE_LIMIT_AI)
async def generate_plan(request: Request, req: PlanGenerationRequest, user: User = Depends(get_current_user)):
    try:
        result = await planner_service.generate_workflow_steps(req.prompt, user_id=str(user.id))
        return {"success": True, **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
@limiter.limit(settings.RATE_LIMIT_AI)
async def chat(request: Request, req: ChatRequest, user: User = Depends(get_current_user)):
    from app.ai import llm_service
    import asyncio
    try:
        reply = await asyncio.wait_for(
            llm_service.generate(
                prompt=req.message,
                system="You are ACO (Autonomous Computer Operator), a friendly and helpful AI assistant. You can also control computers to perform tasks like browsing the web, sending emails, running terminal commands, and managing files. Answer conversationally. Be concise but helpful. If the user asks you to do something on the computer, tell them you'll help them with that.",
                temperature=0.7,
                max_tokens=500,
            ),
            timeout=30.0,
        )
        return {"success": True, "reply": reply or "I'm not sure how to respond to that."}
    except asyncio.TimeoutError:
        return {"success": True, "reply": "I took too long to think about that. Could you rephrase?"}
    except Exception as e:
        return {"success": True, "reply": f"I encountered an error: {str(e)}"}

@router.post("/{id}/execute")
async def execute_workflow(id: str, user: User = Depends(get_current_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    if db_manager.use_memory:
        doc = await memory_db.find_one("workflows", {"_id": ObjectId(id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if str(doc.get("owner_id", "")) != str(user.id):
            raise HTTPException(status_code=403, detail="Access denied")
        from app.infrastructure.db.models import Workflow as WF
        steps_obj = []
        for s in doc.get("steps", []):
            steps_obj.append(Step(**s) if isinstance(s, dict) else s)
        workflow_obj = WF(title=doc["title"], description=doc.get("description",""), owner_id=user.id, steps=steps_obj)
        workflow_obj.id = ObjectId(id)
        try:
            execution_id = await workflow_engine.start_execution(workflow_obj, user.id)
            return {"success": True, "execution_id": execution_id}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    workflow = await Workflow.get(ObjectId(id))
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if str(workflow.owner_id) != str(user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        execution_id = await workflow_engine.start_execution(workflow.id, user.id)
        return {"success": True, "execution_id": execution_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))