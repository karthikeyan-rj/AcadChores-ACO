from fastapi import APIRouter
from app.api.v1 import auth, workflows, executions, permissions, search, plugins, providers, dashboard

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(executions.router, prefix="/executions", tags=["executions"])
api_router.include_router(permissions.router, prefix="/permissions", tags=["permissions"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(plugins.router, prefix="/plugins", tags=["plugins"])
api_router.include_router(providers.router, prefix="/providers", tags=["providers"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
