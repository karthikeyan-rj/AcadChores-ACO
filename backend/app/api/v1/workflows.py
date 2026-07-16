from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Dict, Any, Optional
from bson import ObjectId
from pydantic import BaseModel
from beanie import PydanticObjectId
from datetime import datetime
import uuid

from app.core.database import db_manager
from app.core.config import settings
from app.core.rate_limit import limiter
from app.infrastructure.db.models import Workflow, Step, User, ChatMessage
from app.infrastructure.memory_db import memory_db
from app.services.planner import planner_service
from app.services.workflow_engine import workflow_engine
from app.services.intent_classifier import classify_intent
from app.services.conversation_context import build_entity_context, resolve_references, check_reference_validity, build_context_summary
from app.api.deps import get_current_user, get_user_id

router = APIRouter()


async def _save_chat_message(user_id, conversation_id: str, role: str, message_type: str,
                             content: str, workflow_id: str = None, execution_id: str = None,
                             metadata: dict = None) -> dict:
    msg = {
        "user_id": str(user_id),
        "conversation_id": conversation_id,
        "role": role,
        "message_type": message_type,
        "content": content,
        "workflow_id": workflow_id,
        "execution_id": execution_id,
        "metadata": metadata or {},
        "created_at": datetime.utcnow().isoformat(),
    }
    if db_manager.use_memory:
        oid = await memory_db.insert("chat_messages", msg)
        msg["_id"] = str(oid)
    else:
        doc = ChatMessage(
            user_id=user_id, conversation_id=conversation_id,
            role=role, message_type=message_type, content=content,
            workflow_id=workflow_id, execution_id=execution_id,
            metadata=metadata or {},
        )
        await doc.insert()
        msg["_id"] = str(doc.id)
    return msg


async def _get_conversation_messages(user_id, conversation_id: str, limit: int = 200) -> List[dict]:
    if db_manager.use_memory:
        all_msgs = await memory_db.find("chat_messages", {"user_id": str(user_id), "conversation_id": conversation_id})
        all_msgs.sort(key=lambda m: m.get("created_at", ""))
        return all_msgs[:limit]
    else:
        msgs = await ChatMessage.find(
            ChatMessage.user_id == user_id,
            ChatMessage.conversation_id == conversation_id,
        ).sort(ChatMessage.created_at).limit(limit).to_list()
        return [_msg_to_dict(m) for m in msgs]


async def _get_user_conversations(user_id, limit: int = 50) -> List[dict]:
    if db_manager.use_memory:
        all_msgs = await memory_db.find("chat_messages", {"user_id": str(user_id)})
        conv_map: Dict[str, dict] = {}
        for m in all_msgs:
            cid = m.get("conversation_id", "")
            if cid not in conv_map:
                conv_map[cid] = {
                    "conversation_id": cid,
                    "title": "",
                    "message_count": 0,
                    "last_message_at": m.get("created_at", ""),
                    "has_workflow": False,
                }
            conv = conv_map[cid]
            conv["message_count"] += 1
            if m.get("message_type") == "user" and not conv["title"]:
                conv["title"] = m.get("content", "")[:80]
            if m.get("workflow_id"):
                conv["has_workflow"] = True
            if m.get("created_at", "") > conv["last_message_at"]:
                conv["last_message_at"] = m.get("created_at", "")
        conversations = sorted(conv_map.values(), key=lambda c: c["last_message_at"], reverse=True)
        return conversations[:limit]
    else:
        pipeline = [
            {"$match": {"user_id": user_id}},
            {"$sort": {"created_at": 1}},
            {"$group": {
                "_id": "$conversation_id",
                "title": {"$first": "$content"},
                "message_count": {"$sum": 1},
                "last_message_at": {"$max": "$created_at"},
                "has_workflow": {"$max": {"$cond": [{"$ne": ["$workflow_id", None]}, 1, 0]}},
            }},
            {"$sort": {"last_message_at": -1}},
            {"$limit": limit},
        ]
        results = await ChatMessage.aggregate(pipeline).to_list()
        return [
            {
                "conversation_id": r["_id"],
                "title": (r.get("title") or "")[:80],
                "message_count": r.get("message_count", 0),
                "last_message_at": r.get("last_message_at", ""),
                "has_workflow": bool(r.get("has_workflow")),
            }
            for r in results
        ]


def _msg_to_dict(m) -> dict:
    return {
        "_id": str(m.id),
        "user_id": str(m.user_id),
        "conversation_id": m.conversation_id,
        "role": m.role,
        "message_type": m.message_type,
        "content": m.content,
        "workflow_id": m.workflow_id,
        "execution_id": m.execution_id,
        "metadata": m.metadata or {},
        "created_at": m.created_at.isoformat() if m.created_at else "",
    }


class CreateWorkflowRequest(BaseModel):
    title: str
    description: str
    steps: List[Step]


class PlanGenerationRequest(BaseModel):
    prompt: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class PlanGenerationResponse(BaseModel):
    success: bool
    steps: List[Dict[str, Any]]
    planner_metadata: Optional[Dict[str, Any]] = None


ACTIVE_STATES = {"Planning", "Executing", "Waiting", "Retry", "Stopping"}


async def _has_active_workflow(user_id) -> bool:
    """Check if the user has any workflow in an active state."""
    if db_manager.use_memory:
        all_execs = await memory_db.find("workflow_executions", {"user_id": str(user_id)})
        return any(d.get("status") in ACTIVE_STATES for d in all_execs)
    else:
        from app.infrastructure.db.models import WorkflowExecution
        active = await WorkflowExecution.find(
            WorkflowExecution.user_id == user_id,
            WorkflowExecution.status.in_(list(ACTIVE_STATES))
        ).first_or_none()
        return active is not None


async def _get_active_execution(user_id) -> Optional[dict]:
    """Get the active execution for a user, if any."""
    if db_manager.use_memory:
        all_execs = await memory_db.find("workflow_executions", {"user_id": str(user_id)})
        active = [d for d in all_execs if d.get("status") in ACTIVE_STATES]
        return active[0] if active else None
    else:
        from app.infrastructure.db.models import WorkflowExecution
        active = await WorkflowExecution.find(
            WorkflowExecution.user_id == user_id,
            WorkflowExecution.status.in_(list(ACTIVE_STATES))
        ).sort(-WorkflowExecution.started_at).first_or_none()
        if not active:
            return None
        return {
            "_id": str(active.id),
            "workflow_id": str(active.workflow_id),
            "title": active.title or "",
            "description": active.description or "",
            "status": active.status,
            "current_step_index": active.current_step_index,
            "total_steps": active.total_steps,
            "started_at": active.started_at.isoformat() if active.started_at else None,
        }


@router.get("/active")
async def get_active_workflow(user: User = Depends(get_current_user)):
    """Return the current active workflow for the authenticated user."""
    active = await _get_active_execution(user.id)
    return {"success": True, "active": active}


@router.get("/entity-context")
async def get_entity_context(conversation_id: str, user: User = Depends(get_current_user)):
    """Return extracted entity context for a conversation."""
    recent_messages = await _get_conversation_messages(user.id, conversation_id, limit=20)
    entities = build_entity_context(recent_messages)
    return {"success": True, "entities": entities}


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
            "created_at": datetime.utcnow().isoformat(),
        }
        oid = await memory_db.insert("workflows", doc)
        return {"_id": str(oid), "title": req.title, "steps": steps_dicts}
    workflow = Workflow(
        title=req.title,
        description=req.description,
        owner_id=user.id,
        steps=[Step(**s) if isinstance(s, dict) else s for s in req.steps],
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

    conversation_id = req.conversation_id or str(uuid.uuid4())
    user_id = user.id

    await _save_chat_message(user_id, conversation_id, "user", "user", req.message)

    # Load conversation context for reference resolution
    recent_messages = await _get_conversation_messages(user_id, conversation_id, limit=20)
    entities = build_entity_context(recent_messages)

    # Resolve ambiguous references (e.g., "delete that file" → "delete C:\...\factorial.py")
    resolved_prompt = resolve_references(req.message, entities)

    # Check if reference points to a deleted file
    clarification = check_reference_validity(resolved_prompt, entities)
    if clarification:
        await _save_chat_message(user_id, conversation_id, "assistant", "assistant", clarification)
        return {
            "success": True, "reply": clarification,
            "conversation_id": conversation_id,
            "intent": {"intent": "clarification_required", "confidence": 0.9, "reason": clarification},
        }

    # If prompt was resolved, use the resolved version
    prompt_to_process = resolved_prompt if resolved_prompt != req.message else req.message

    intent = classify_intent(prompt_to_process)
    intent_type = intent.get("intent", "conversation")

    if intent_type == "conversation":
        # Build context summary for conversational replies too
        context_summary = build_context_summary(entities, recent_messages)
        system_prompt = "You are ACO (Autonomous Computer Operator), a friendly and helpful AI assistant. You can control computers to perform tasks like browsing the web, sending emails, running terminal commands, and managing files. Answer conversationally. Be concise but helpful."
        if context_summary:
            system_prompt += f"\n\nConversation context:\n{context_summary}"

        try:
            reply = await asyncio.wait_for(
                llm_service.generate(
                    prompt=prompt_to_process,
                    system=system_prompt,
                    temperature=0.7,
                    max_tokens=500,
                ),
                timeout=30.0,
            )
            assistant_text = reply or "I'm not sure how to respond to that."
        except asyncio.TimeoutError:
            assistant_text = "I took too long to think about that. Could you rephrase?"
        except Exception as e:
            assistant_text = f"I encountered an error: {str(e)}"

        await _save_chat_message(user_id, conversation_id, "assistant", "assistant", assistant_text)
        return {
            "success": True, "reply": assistant_text,
            "conversation_id": conversation_id,
            "intent": intent,
        }

    if intent_type == "clarification_required":
        clarification = intent.get("reason", "Could you provide more details?")
        await _save_chat_message(user_id, conversation_id, "assistant", "assistant", clarification)
        return {
            "success": True, "reply": clarification,
            "conversation_id": conversation_id,
            "intent": intent,
        }

    # Action intent: build context for the planner
    context_summary = build_context_summary(entities, recent_messages)
    planner_prompt = prompt_to_process
    if context_summary:
        planner_prompt = f"{prompt_to_process}\n\n[Conversation context]\n{context_summary}"

    try:
        plan_result = await planner_service.generate_workflow_steps(planner_prompt, user_id=str(user.id))
        steps = plan_result.get("steps", [])
        metadata = plan_result.get("planner_metadata", {})
        pending = plan_result.get("pending_confirmation")

        step_summary = f"Generated {len(steps)} step(s)." if steps else "Could not generate a plan."
        planner_source = metadata.get("planner_source", "unknown")
        quality = metadata.get("quality_score", 0)

        plan_content = f"I created a workflow with {len(steps)} step(s) ({planner_source}, quality: {quality}). Review the steps before execution."
        if pending:
            plan_content += f"\n{pending.get('message', 'Confirmation required.')}"

        # Build entity metadata to persist with the plan message
        plan_entities = {
            "entities": entities,
            "resolved_from": req.message if resolved_prompt != req.message else None,
            "resolved_to": resolved_prompt if resolved_prompt != req.message else None,
        }

        await _save_chat_message(user_id, conversation_id, "assistant", "workflow_plan", plan_content,
                                 metadata={"planner_source": planner_source, "quality_score": quality, "step_count": len(steps), **plan_entities})

        return {
            "success": True, "steps": steps, "planner_metadata": metadata,
            "pending_confirmation": pending,
            "conversation_id": conversation_id,
            "intent": intent,
            "resolved_prompt": resolved_prompt if resolved_prompt != req.message else None,
        }
    except ValueError as e:
        error_msg = f"Could not generate a plan: {str(e)}"
        await _save_chat_message(user_id, conversation_id, "assistant", "error", error_msg)
        return {"success": False, "reply": error_msg, "conversation_id": conversation_id, "intent": intent}
    except Exception as e:
        error_msg = f"Error generating plan: {str(e)}"
        await _save_chat_message(user_id, conversation_id, "assistant", "error", error_msg)
        return {"success": False, "reply": error_msg, "conversation_id": conversation_id, "intent": intent}


@router.get("/conversations")
async def list_conversations(user: User = Depends(get_current_user)):
    conversations = await _get_user_conversations(user.id)
    return {"success": True, "conversations": conversations}


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, user: User = Depends(get_current_user)):
    messages = await _get_conversation_messages(user.id, conversation_id)
    return {"success": True, "conversation_id": conversation_id, "messages": messages}


@router.post("/{id}/execute")
async def execute_workflow(id: str, user: User = Depends(get_current_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    # Enforce single active workflow per user
    try:
        if await _has_active_workflow(user.id):
            raise HTTPException(status_code=409, detail="An active workflow already exists for this user. Stop or wait for it to finish.")
    except HTTPException:
        raise
    except Exception:
        pass

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
        workflow_obj = WF(title=doc["title"], description=doc.get("description", ""), owner_id=user.id, steps=steps_obj)
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
