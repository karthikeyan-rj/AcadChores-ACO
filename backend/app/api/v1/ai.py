"""AI provider, credential, model, and settings API endpoints.

All credential operations use credential_id (not provider name) for
multi-key support. Provider is inferred from the stored credential.
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.infrastructure.db.models import User, UserSettings, Conversation
from app.api.deps import get_current_user
from app.ai.registry import provider_registry
from app.ai.catalogue import model_catalogue
from app.ai.router import ai_router
from app.ai.providers.base.health import health_cache
from app.services.credential_service import credential_service, CredentialError

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class CredentialSaveRequest(BaseModel):
    provider: str
    api_key: str = Field(min_length=10)
    label: str = ""
    is_default: bool = False


class CredentialUpdateRequest(BaseModel):
    label: Optional[str] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class AISettingsUpdate(BaseModel):
    ai_local_only: Optional[bool] = None
    fallback_to_local: Optional[bool] = None
    default_provider: Optional[str] = None
    default_model: Optional[str] = None
    default_credential_id: Optional[str] = None
    default_reasoning_level: Optional[str] = None


class ConversationModelSelection(BaseModel):
    preferred_provider: Optional[str] = None
    preferred_model: Optional[str] = None
    preferred_credential_id: Optional[str] = None
    reasoning_level: Optional[str] = None


# ---------------------------------------------------------------------------
# Provider endpoints
# ---------------------------------------------------------------------------

@router.get("/providers")
async def list_providers(user: User = Depends(get_current_user)):
    """List all registered providers with availability and capabilities."""
    health_results = await ai_router.health_check() if hasattr(ai_router, 'health_check') else {}
    all_providers = provider_registry.get_all()
    result = []
    for name, provider in all_providers.items():
        h = health_results.get(name)
        result.append({
            "id": name,
            "name": name.title(),
            "available": h.available if h else False,
            "latency_ms": h.latency_ms if h else 0,
            "error": h.error if h else None,
            "capabilities": {
                "supports_streaming": provider.capabilities.supports_streaming,
                "supports_embeddings": provider.capabilities.supports_embeddings,
                "supports_model_discovery": provider.capabilities.supports_model_discovery,
                "supports_structured_output": provider.capabilities.supports_structured_output,
                "supports_reasoning": provider.capabilities.supports_reasoning,
                "supports_tools": provider.capabilities.supports_tools,
                "supports_vision": provider.capabilities.supports_vision,
            },
        })
    return {"providers": result}


@router.get("/providers/{provider_id}/health")
async def provider_health(provider_id: str, user: User = Depends(get_current_user)):
    provider = provider_registry.get(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found")
    cached = await health_cache.get(provider_id)
    if cached:
        return cached
    health = await provider.health()
    await health_cache.set(provider_id, health)
    return health


# ---------------------------------------------------------------------------
# Model endpoints
# ---------------------------------------------------------------------------

@router.get("/models")
async def list_models(provider_id: Optional[str] = None, user: User = Depends(get_current_user)):
    """List ACO-compatible models from static catalogue and dynamic discovery."""
    models = await model_catalogue.get_models(provider_id)
    return {"models": models}


@router.get("/models/{provider_id}/{model_id}")
async def get_model(provider_id: str, model_id: str, user: User = Depends(get_current_user)):
    info = await model_catalogue.get_model_info(provider_id, model_id)
    if not info:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found for '{provider_id}'")
    return info


# ---------------------------------------------------------------------------
# Credential endpoints (credential_id-based)
# ---------------------------------------------------------------------------

@router.get("/credentials")
async def list_credentials(user: User = Depends(get_current_user)):
    creds = await credential_service.list_credentials(str(user.id))
    return {"credentials": creds}


@router.post("/credentials")
async def save_credential(body: CredentialSaveRequest, user: User = Depends(get_current_user)):
    provider = body.provider.lower().strip()
    valid_providers = list(provider_registry.get_all().keys())
    if provider not in valid_providers:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{provider}'. Available: {valid_providers}")
    try:
        doc = await credential_service.save_key(
            user_id=str(user.id),
            provider=provider,
            api_key=body.api_key.strip(),
            label=body.label,
            is_default=body.is_default,
        )
        return {
            "success": True,
            "id": str(doc.id),
            "provider": doc.provider,
            "label": doc.label,
            "key_hint": doc.key_hint,
            "is_default": doc.is_default,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/credentials/{credential_id}")
async def update_credential(credential_id: str, body: CredentialUpdateRequest, user: User = Depends(get_current_user)):
    from app.infrastructure.db.models import UserApiKey
    doc = await UserApiKey.find_one(
        UserApiKey.id == credential_id,
        UserApiKey.user_id == str(user.id),
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Credential not found")
    if body.label is not None:
        doc.label = body.label
    if body.is_active is not None:
        doc.is_active = body.is_active
    if body.is_default is not None and body.is_default:
        await credential_service.set_default(str(user.id), credential_id)
    doc.updated_at = datetime.now(timezone.utc)
    await doc.save()
    return {"success": True}


@router.delete("/credentials/{credential_id}")
async def delete_credential(credential_id: str, user: User = Depends(get_current_user)):
    deleted = await credential_service.delete_key(str(user.id), credential_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credential not found")
    return {"success": True}


@router.post("/credentials/{credential_id}/validate")
async def validate_credential(credential_id: str, user: User = Depends(get_current_user)):
    result = await credential_service.validate_key(str(user.id), credential_id)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Validation failed"))
    return result


# ---------------------------------------------------------------------------
# AI settings endpoints
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_ai_settings(user: User = Depends(get_current_user)):
    from app.core.database import db_manager
    from app.infrastructure.memory_db import memory_db

    user_id = str(user.id)
    if db_manager.use_memory:
        doc = await memory_db.find_one("user_settings", {"user_id": user_id})
        if not doc:
            doc = {"user_id": user_id, "ai_local_only": True, "fallback_to_local": True,
                   "default_provider": "ollama", "default_model": "", "default_credential_id": None,
                   "default_reasoning_level": "balanced"}
            await memory_db.insert("user_settings", doc)
            doc = await memory_db.find_one("user_settings", {"user_id": user_id})
        return {
            "ai_local_only": doc.get("ai_local_only", True),
            "fallback_to_local": doc.get("fallback_to_local", True),
            "default_provider": doc.get("default_provider", "ollama"),
            "default_model": doc.get("default_model", ""),
            "default_credential_id": doc.get("default_credential_id"),
            "default_reasoning_level": doc.get("default_reasoning_level", "balanced"),
        }

    from beanie import PydanticObjectId
    doc = await UserSettings.find_one(UserSettings.user_id == PydanticObjectId(user_id))
    if not doc:
        doc = UserSettings(user_id=PydanticObjectId(user_id))
        await doc.insert()
    return {
        "ai_local_only": doc.ai_local_only,
        "fallback_to_local": doc.fallback_to_local,
        "default_provider": doc.default_provider,
        "default_model": doc.default_model,
        "default_credential_id": doc.default_credential_id,
        "default_reasoning_level": doc.default_reasoning_level,
    }


@router.put("/settings")
async def update_ai_settings(body: AISettingsUpdate, user: User = Depends(get_current_user)):
    from app.core.database import db_manager
    from app.infrastructure.memory_db import memory_db

    user_id = str(user.id)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if db_manager.use_memory:
        doc = await memory_db.find_one("user_settings", {"user_id": user_id})
        if not doc:
            doc = {"user_id": user_id}
        for k, v in update_data.items():
            doc[k] = v
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        await memory_db.update("user_settings", {"user_id": user_id}, doc)
        return doc

    from beanie import PydanticObjectId
    doc = await UserSettings.find_one(UserSettings.user_id == PydanticObjectId(user_id))
    if not doc:
        doc = UserSettings(user_id=PydanticObjectId(user_id))
        await doc.insert()
    for k, v in update_data.items():
        setattr(doc, k, v)
    doc.updated_at = datetime.now(timezone.utc)
    await doc.save()
    return {
        "ai_local_only": doc.ai_local_only,
        "fallback_to_local": doc.fallback_to_local,
        "default_provider": doc.default_provider,
        "default_model": doc.default_model,
        "default_credential_id": doc.default_credential_id,
        "default_reasoning_level": doc.default_reasoning_level,
    }


# ---------------------------------------------------------------------------
# Conversation model selection
# ---------------------------------------------------------------------------

@router.put("/conversations/{conversation_id}/model-selection")
async def set_conversation_model(conversation_id: str, body: ConversationModelSelection, user: User = Depends(get_current_user)):
    from app.core.database import db_manager
    from app.infrastructure.memory_db import memory_db

    user_id = str(user.id)
    update_data = body.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")

    if db_manager.use_memory:
        doc = await memory_db.find_one("conversations", {"conversation_id": conversation_id, "user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="Conversation not found")
        for k, v in update_data.items():
            doc[k] = v
        doc["updated_at"] = datetime.now(timezone.utc).isoformat()
        await memory_db.update("conversations", {"conversation_id": conversation_id}, doc)
        return {k: doc.get(k) for k in update_data}

    from beanie import PydanticObjectId
    doc = await Conversation.find_one(
        Conversation.conversation_id == conversation_id,
        Conversation.user_id == PydanticObjectId(user_id),
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Conversation not found")
    for k, v in update_data.items():
        setattr(doc, k, v)
    doc.updated_at = datetime.now(timezone.utc)
    await doc.save()
    return {k: getattr(doc, k) for k in update_data}
