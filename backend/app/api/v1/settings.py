from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.infrastructure.db.models import User, UserSettings
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

async def _get_or_create(user_id: str) -> UserSettings:
    """Return the user's settings document, creating defaults if absent."""
    from beanie import PydanticObjectId
    oid = PydanticObjectId(user_id)
    existing = await UserSettings.find_one(UserSettings.user_id == oid)
    if existing:
        return existing
    doc = UserSettings(user_id=oid)
    await doc.insert()
    return doc


def _to_response(settings: UserSettings, api_key_hint: Optional[str], api_key_configured: bool) -> dict:
    return SettingsResponse(
        cloud_fallback_enabled=settings.cloud_fallback_enabled,
        cloud_provider=settings.cloud_provider,
        cloud_model=settings.cloud_model,
        api_key_configured=api_key_configured,
        api_key_hint=api_key_hint,
        workflow_quality_threshold=settings.workflow_quality_threshold,
        local_planner_retry_count=settings.local_planner_retry_count,
    ).model_dump()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=None)
async def get_settings(user: User = Depends(get_current_user)):
    user_id = str(user.id)
    s = await _get_or_create(user_id)
    key_hint = await get_api_key_hint(user_id, s.cloud_provider)
    return _to_response(s, api_key_hint=key_hint, api_key_configured=key_hint is not None)


@router.patch("", response_model=None)
async def update_settings(body: SettingsUpdate, user: User = Depends(get_current_user)):
    user_id = str(user.id)
    s = await _get_or_create(user_id)

    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    for field_name, value in update_data.items():
        setattr(s, field_name, value)

    s.updated_at = datetime.utcnow()
    await s.save()

    key_hint = await get_api_key_hint(user_id, s.cloud_provider)
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
