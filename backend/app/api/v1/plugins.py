from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

from app.api.deps import get_current_active_user
from app.infrastructure.db.models import User
from app.plugin_sdk.loader import plugin_loader, PluginDescriptor
from app.plugin_sdk.sandbox import plugin_sandbox

router = APIRouter()

class RunPluginRequest(BaseModel):
    plugin_name: str
    inputs: Dict[str, Any]

@router.get("", response_model=List[PluginDescriptor])
async def list_plugins(current_user: User = Depends(get_current_active_user)):
    return plugin_loader.list_plugins()

@router.post("/register")
async def register_plugin(
    descriptor: PluginDescriptor,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to register plugins")
    try:
        plugin_loader.register(descriptor)
        return {"success": True, "message": f"Plugin {descriptor.name} registered."}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/run")
async def run_plugin(
    req: RunPluginRequest,
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin role required to run plugins")
    plugin = plugin_loader.get_plugin(req.plugin_name)
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found.")

    # Execute custom plugin safely inside restricted sandbox
    result = plugin_sandbox.execute(
        code_str=plugin.code,
        entry_point=plugin.entry_point,
        inputs=req.inputs
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Sandbox execution failure."))
    return result
