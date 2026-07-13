from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from app.ai import llm_service, provider_manager
from app.ai.registry import provider_registry
from app.ai.capabilities import capability_registry
from app.ai.providers.base.types import ProviderHealth, ModelInfo, ProviderMetrics

router = APIRouter()


@router.get("")
async def list_providers():
    health_results = await llm_service.health()
    return {
        "providers": [
            {
                "name": name,
                "available": health.available,
                "model": health.model,
                "latency_ms": health.latency_ms,
                "error": health.error,
                "gpu_available": health.gpu_available,
            }
            for name, health in health_results.items()
        ]
    }


@router.get("/{name}/health")
async def provider_health(name: str):
    results = await llm_service.health(name)
    if name not in results:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    return results[name]


@router.get("/{name}/models")
async def provider_models(name: str):
    results = await llm_service.list_models(name)
    if name not in results:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    return {"provider": name, "models": [m.__dict__ for m in results[name]]}


@router.get("/{name}/metrics")
async def provider_metrics(name: str):
    metrics = llm_service.get_metrics(name)
    if not metrics:
        return {"provider": name, "metrics": None}
    m = list(metrics.values())[0]
    return {
        "provider": m.provider,
        "model": m.model,
        "total_requests": m.total_requests,
        "total_errors": m.total_errors,
        "success_rate": m.success_rate,
        "avg_latency_ms": m.avg_latency_ms,
        "total_tokens_input": m.total_tokens_input,
        "total_tokens_output": m.total_tokens_output,
        "total_cost": m.total_cost,
    }


class DownloadModelRequest(BaseModel):
    model_id: str


@router.post("/{name}/models/download")
async def download_model(name: str, req: DownloadModelRequest):
    provider = provider_registry.get(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    success = await provider.download_model(req.model_id)
    return {"success": success, "model_id": req.model_id}


@router.delete("/{name}/models/{model_id}")
async def delete_model(name: str, model_id: str):
    provider = provider_registry.get(name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{name}' not found")
    success = await provider.delete_model(model_id)
    return {"success": success, "model_id": model_id}


@router.get("/metrics")
async def all_metrics():
    all_metrics = llm_service.get_metrics()
    return [
        {
            "provider": m.provider,
            "model": m.model,
            "total_requests": m.total_requests,
            "total_errors": m.total_errors,
            "success_rate": m.success_rate,
            "avg_latency_ms": m.avg_latency_ms,
            "total_tokens_input": m.total_tokens_input,
            "total_tokens_output": m.total_tokens_output,
            "total_cost": m.total_cost,
        }
        for m in all_metrics.values()
    ]


@router.get("/capabilities")
async def list_capabilities():
    return {
        "agents": {
            agent_type: {
                "actions": list(caps.actions),
                "capabilities": [
                    {"action": c.action, "description": c.description}
                    for c in caps.capabilities
                ],
            }
            for agent_type, caps in capability_registry.all_agents().items()
        },
        "total_agents": len(capability_registry.all_agents()),
        "total_actions": len(capability_registry.all_actions()),
    }


@router.get("/capabilities/find/{action}")
async def find_agents_for_action(action: str):
    agents = capability_registry.find_agents(action)
    return {"action": action, "agents": agents, "available": len(agents) > 0}
