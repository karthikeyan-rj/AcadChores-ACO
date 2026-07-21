from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.core.database import db_manager
from app.infrastructure.db.models import User, UserSettings
from app.infrastructure.memory_db import memory_db
from app.api.deps import get_current_user
from app.services.credential_store import (
    save_api_key, get_api_key_hint, delete_api_key, list_api_keys,
)

router = APIRouter()

VALID_PROVIDERS = ("openai", "anthropic", "gemini")
VALID_APPROVAL = ("allow", "ask")
MIN_QUALITY = 50
MAX_QUALITY = 100
MIN_RETRIES = 0
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Pydantic request / response schemas
# ---------------------------------------------------------------------------

class SettingsResponse(BaseModel):
    cloud_fallback_enabled: bool
    cloud_provider: str
    cloud_model: str
    api_key_configured: bool = False
    api_key_hint: Optional[str] = None
    workflow_quality_threshold: int
    local_planner_retry_count: int


class SettingsUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    cloud_fallback_enabled: Optional[bool] = None
    cloud_provider: Optional[str] = None
    cloud_model: Optional[str] = None
    workflow_quality_threshold: Optional[int] = None
    local_planner_retry_count: Optional[int] = None

    @field_validator("cloud_provider")
    @classmethod
    def validate_provider(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PROVIDERS:
            raise ValueError(f"Provider must be one of: {', '.join(VALID_PROVIDERS)}")
        return v

    @field_validator("workflow_quality_threshold")
    @classmethod
    def validate_quality(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < MIN_QUALITY or v > MAX_QUALITY):
            raise ValueError(f"Quality threshold must be between {MIN_QUALITY} and {MAX_QUALITY}")
        return v

    @field_validator("local_planner_retry_count")
    @classmethod
    def validate_retries(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < MIN_RETRIES or v > MAX_RETRIES):
            raise ValueError(f"Retry count must be between {MIN_RETRIES} and {MAX_RETRIES}")
        return v


class ApiKeySaveRequest(BaseModel):
    provider: str
    api_key: str


class ApiKeyInfo(BaseModel):
    provider: str
    key_hint: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_or_create(user_id: str):
    """Return the user's settings, creating defaults if absent. Works in both memory and MongoDB modes."""
    if db_manager.use_memory:
        existing = await memory_db.find_one("user_settings", {"user_id": str(user_id)})
        if existing:
            return existing
        defaults = {
            "user_id": str(user_id),
            "cloud_fallback_enabled": False,
            "cloud_provider": "openai",
            "cloud_model": "gpt-4o-mini",
            "workflow_quality_threshold": 70,
            "local_planner_retry_count": 1,
        }
        await memory_db.insert("user_settings", defaults)
        return await memory_db.find_one("user_settings", {"user_id": str(user_id)})
    from beanie import PydanticObjectId
    oid = PydanticObjectId(user_id)
    existing = await UserSettings.find_one(UserSettings.user_id == oid)
    if existing:
        return existing
    doc = UserSettings(user_id=oid)
    await doc.insert()
    return doc


def _get_attr(obj, key, default=None):
    """Get attribute from either an object or dict."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_response(s, api_key_hint: Optional[str], api_key_configured: bool) -> dict:
    return SettingsResponse(
        cloud_fallback_enabled=_get_attr(s, "cloud_fallback_enabled", False),
        cloud_provider=_get_attr(s, "cloud_provider", "openai"),
        cloud_model=_get_attr(s, "cloud_model", "gpt-4o-mini"),
        api_key_configured=api_key_configured,
        api_key_hint=api_key_hint,
        workflow_quality_threshold=_get_attr(s, "workflow_quality_threshold", 70),
        local_planner_retry_count=_get_attr(s, "local_planner_retry_count", 1),
    ).model_dump()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=None)
async def get_settings(user: User = Depends(get_current_user)):
    user_id = str(user.id)
    s = await _get_or_create(user_id)
    provider = _get_attr(s, "cloud_provider", "openai")
    key_hint = await get_api_key_hint(user_id, provider)
    return _to_response(s, api_key_hint=key_hint, api_key_configured=key_hint is not None)


@router.patch("", response_model=None)
async def update_settings(body: SettingsUpdate, user: User = Depends(get_current_user)):
    user_id = str(user.id)
    s = await _get_or_create(user_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if db_manager.use_memory:
        for field_name, value in update_data.items():
            s[field_name] = value
        s["updated_at"] = datetime.now(timezone.utc).isoformat()
        await memory_db.update("user_settings", {"user_id": user_id}, s)
    else:
        for field_name, value in update_data.items():
            setattr(s, field_name, value)
        s.updated_at = datetime.now(timezone.utc)
        await s.save()

    key_hint = await get_api_key_hint(user_id, _get_attr(s, "cloud_provider", "openai"))
    return _to_response(s, api_key_hint=key_hint, api_key_configured=key_hint is not None)


# ---------------------------------------------------------------------------
# API-key sub-routes (scoped to settings context)
# ---------------------------------------------------------------------------

@router.get("/api-keys")
async def get_api_keys(user: User = Depends(get_current_user)):
    keys = await list_api_keys(str(user.id))
    return {"keys": keys}


@router.post("/api-keys")
async def save_api_key_route(body: ApiKeySaveRequest, user: User = Depends(get_current_user)):
    provider = body.provider.lower().strip()
    if provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Provider must be one of: {', '.join(VALID_PROVIDERS)}")
    if not body.api_key or len(body.api_key.strip()) < 10:
        raise HTTPException(status_code=400, detail="Invalid API key")
    result = await save_api_key(str(user.id), provider, body.api_key.strip())
    return {"success": True, **result}


@router.delete("/api-keys/{provider}")
async def delete_api_key_route(provider: str, user: User = Depends(get_current_user)):
    deleted = await delete_api_key(str(user.id), provider)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No API key found for provider '{provider}'")
    return {"success": True, "deleted_provider": provider}
