from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel

from app.core.config import settings
from app.core.rate_limit import limiter
from app.infrastructure.db.models import User
from app.api.deps import get_current_user
from app.services.credential_store import save_api_key, get_api_key_hint, delete_api_key, list_api_keys
from app.services.fallback_tracker import get_usage_stats
from app.services.workflow_validator import WorkflowValidator

router = APIRouter()


class SaveApiKeyRequest(BaseModel):
    provider: str
    api_key: str


class ApiKeyInfo(BaseModel):
    provider: str
    key_hint: str


class ApiKeyStatusResponse(BaseModel):
    keys: List[ApiKeyInfo]


class CloudSettingsResponse(BaseModel):
    cloud_fallback_enabled: bool
    cloud_ai_provider: str
    cloud_ai_model: str
    daily_limit: int
    usage: dict


class ValidateWorkflowRequest(BaseModel):
    workflow: dict
    prompt: str = ""


@router.get("/api-keys")
async def get_api_keys(user: User = Depends(get_current_user)):
    keys = await list_api_keys(str(user.id))
    return {"keys": keys}


@router.post("/api-keys")
@limiter.limit("5/minute")
async def save_api_key_route(request: Request, req: SaveApiKeyRequest, user: User = Depends(get_current_user)):
    provider = req.provider.lower().strip()
    if provider not in ("openai", "anthropic", "gemini"):
        raise HTTPException(status_code=400, detail="Provider must be one of: openai, anthropic, gemini")
    if not req.api_key or len(req.api_key.strip()) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key")
    result = await save_api_key(str(user.id), provider, req.api_key.strip())
    return {"success": True, **result}


@router.delete("/api-keys/{provider}")
async def delete_api_key_route(provider: str, user: User = Depends(get_current_user)):
    deleted = await delete_api_key(str(user.id), provider)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No API key found for provider '{provider}'")
    return {"success": True, "deleted_provider": provider}


@router.get("/cloud-settings")
async def get_cloud_settings(user: User = Depends(get_current_user)):
    usage = await get_usage_stats(str(user.id), days=1)
    return CloudSettingsResponse(
        cloud_fallback_enabled=getattr(settings, "CLOUD_FALLBACK_ENABLED", False),
        cloud_ai_provider=getattr(settings, "CLOUD_AI_PROVIDER", "openai"),
        cloud_ai_model=getattr(settings, "CLOUD_AI_MODEL", "gpt-4o-mini"),
        daily_limit=getattr(settings, "CLOUD_FALLBACK_DAILY_LIMIT", 20),
        usage=usage,
    )


@router.post("/validate-workflow")
async def validate_workflow_endpoint(req: ValidateWorkflowRequest, user: User = Depends(get_current_user)):
    validator = WorkflowValidator(min_quality_score=getattr(settings, "WORKFLOW_MIN_QUALITY_SCORE", 70))
    result = validator.validate(req.workflow, req.prompt)
    return result
