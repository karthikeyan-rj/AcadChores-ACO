from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
import logging

from app.api.deps import get_current_active_user
from app.infrastructure.db.models import User, PermissionPolicy, Rule
from app.core.event_bus import event_bus

logger = logging.getLogger(__name__)
router = APIRouter()

class UpdatePoliciesRequest(BaseModel):
    rules: List[Rule]

class PermissionResponseRequest(BaseModel):
    request_id: str
    approved: bool

@router.get("/policies", response_model=PermissionPolicy)
async def get_permission_policies(current_user: User = Depends(get_current_active_user)):
    policy = await PermissionPolicy.find_one(PermissionPolicy.role == "user")
    if not policy:
        # Seed default policies if empty
        policy = PermissionPolicy(
            role="user",
            rules=[
                Rule(agent="browser", action="navigate", policy="allow"),
                Rule(agent="browser", action="click", policy="allow"),
                Rule(agent="desktop", action="click", policy="allow"),
                Rule(agent="desktop", action="type", policy="allow"),
                Rule(agent="terminal", action="run", policy="ask")
            ]
        )
        await policy.insert()
    return policy

@router.put("/policies", response_model=PermissionPolicy)
async def update_permission_policies(
    req: UpdatePoliciesRequest,
    current_user: User = Depends(get_current_active_user)
):
    policy = await PermissionPolicy.find_one(PermissionPolicy.role == "user")
    if not policy:
        policy = PermissionPolicy(role="user")
    policy.rules = req.rules
    await policy.save()
    return policy

@router.post("/response")
async def submit_permission_response(
    req: PermissionResponseRequest,
    current_user: User = Depends(get_current_active_user)
):
    """
    Submits a user override response (Allow/Block) for a pending authorization request.
    Publishes the response event to the Event Bus to resolve the waiting future.
    """
    logger.info(f"PERMISSION_RESPONSE: user={current_user.email}, request_id={req.request_id}, approved={req.approved}")
    try:
        await event_bus.publish(
            topic="permission.response",
            sender="PermissionAPI",
            payload={
                "request_id": req.request_id,
                "approved": req.approved
            }
        )
        logger.info(f"PERMISSION_RESPONSE: event published for request_id={req.request_id}")
        return {"success": True}
    except Exception as e:
        logger.error(f"PERMISSION_RESPONSE: failed to publish for request_id={req.request_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
