from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from bson import ObjectId

from app.api.deps import get_current_user, get_user_id
from app.core.database import db_manager
from app.infrastructure.db.models import User, IndexConfig, IndexJob
from app.infrastructure.memory_db import memory_db
from app.services.indexer import file_indexer
from pydantic import BaseModel

router = APIRouter()


class IndexConfigUpdate(BaseModel):
    roots: Optional[List[str]] = None
    enabled: Optional[bool] = None
    interval_seconds: Optional[int] = None
    max_file_size_mb: Optional[int] = None
    exclude_extensions: Optional[List[str]] = None
    exclude_dirs: Optional[List[str]] = None


@router.get("/files")
async def search_indexed_files(
    query: str = Query(..., min_length=1),
    limit: int = Query(50, le=100),
    user: User = Depends(get_current_user)
):
    results = await file_indexer.search(query, user.id, limit)
    return {
        "success": True,
        "results": results
    }


@router.get("/index/config")
async def get_index_config(user: User = Depends(get_current_user)):
    user_id_str = str(user.id)
    if db_manager.use_memory:
        config = await memory_db.find_one("index_configs", {"user_id": user_id_str})
        if not config:
            return {
                "exists": False,
                "config": {
                    "roots": [],
                    "enabled": False,
                    "interval_seconds": 3600,
                    "max_file_size_mb": 100,
                    "exclude_extensions": [".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o"],
                    "exclude_dirs": ["node_modules", ".git", "__pycache__", ".venv", "venv", "AppData", "Windows", "Program Files", "Program Files (x86)"]
                }
            }
        return {
            "exists": True,
            "config": {
                "roots": config.get("roots", []),
                "enabled": config.get("enabled", False),
                "interval_seconds": config.get("interval_seconds", 3600),
                "max_file_size_mb": config.get("max_file_size_mb", 100),
                "exclude_extensions": config.get("exclude_extensions", []),
                "exclude_dirs": config.get("exclude_dirs", [])
            }
        }
    else:
        config = await IndexConfig.find_one(IndexConfig.user_id == user.id)
        if not config:
            return {
                "exists": False,
                "config": {
                    "roots": [],
                    "enabled": False,
                    "interval_seconds": 3600,
                    "max_file_size_mb": 100,
                    "exclude_extensions": [".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o"],
                    "exclude_dirs": ["node_modules", ".git", "__pycache__", ".venv", "venv", "AppData", "Windows", "Program Files", "Program Files (x86)"]
                }
            }
        return {
            "exists": True,
            "config": {
                "roots": config.roots,
                "enabled": config.enabled,
                "interval_seconds": config.interval_seconds,
                "max_file_size_mb": config.max_file_size_mb,
                "exclude_extensions": config.exclude_extensions,
                "exclude_dirs": config.exclude_dirs
            }
        }


@router.post("/index/config")
async def upsert_index_config(
    update: IndexConfigUpdate,
    user: User = Depends(get_current_user)
):
    user_id_str = str(user.id)
    if db_manager.use_memory:
        config = await memory_db.find_one("index_configs", {"user_id": user_id_str})
        if config:
            if update.roots is not None:
                config["roots"] = update.roots
            if update.enabled is not None:
                config["enabled"] = update.enabled
            if update.interval_seconds is not None:
                config["interval_seconds"] = max(60, update.interval_seconds)
            if update.max_file_size_mb is not None:
                config["max_file_size_mb"] = max(1, update.max_file_size_mb)
            if update.exclude_extensions is not None:
                config["exclude_extensions"] = update.exclude_extensions
            if update.exclude_dirs is not None:
                config["exclude_dirs"] = update.exclude_dirs
            await memory_db.update("index_configs", {"_id": config["_id"]}, config)
        else:
            new_config = {
                "user_id": user_id_str,
                "roots": update.roots or [],
                "enabled": update.enabled if update.enabled is not None else False,
                "interval_seconds": update.interval_seconds or 3600,
                "max_file_size_mb": update.max_file_size_mb or 100,
                "exclude_extensions": update.exclude_extensions or [".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o"],
                "exclude_dirs": update.exclude_dirs or ["node_modules", ".git", "__pycache__", ".venv", "venv", "AppData", "Windows", "Program Files", "Program Files (x86)"]
            }
            await memory_db.insert("index_configs", new_config)
    else:
        config = await IndexConfig.find_one(IndexConfig.user_id == user.id)
        if config:
            if update.roots is not None:
                config.roots = update.roots
            if update.enabled is not None:
                config.enabled = update.enabled
            if update.interval_seconds is not None:
                config.interval_seconds = max(60, update.interval_seconds)
            if update.max_file_size_mb is not None:
                config.max_file_size_mb = max(1, update.max_file_size_mb)
            if update.exclude_extensions is not None:
                config.exclude_extensions = update.exclude_extensions
            if update.exclude_dirs is not None:
                config.exclude_dirs = update.exclude_dirs
            await config.save()
        else:
            config = IndexConfig(
                user_id=user.id,
                roots=update.roots or [],
                enabled=update.enabled if update.enabled is not None else False,
                interval_seconds=update.interval_seconds or 3600,
                max_file_size_mb=update.max_file_size_mb or 100,
                exclude_extensions=update.exclude_extensions or [".exe", ".dll", ".so", ".dylib", ".bin", ".obj", ".o"],
                exclude_dirs=update.exclude_dirs or ["node_modules", ".git", "__pycache__", ".venv", "venv", "AppData", "Windows", "Program Files", "Program Files (x86)"]
            )
            await config.insert()
    return {"success": True, "message": "Index configuration saved."}


@router.post("/index/trigger")
async def trigger_index(user: User = Depends(get_current_user)):
    job_id = await file_indexer.trigger_index(user.id)
    if job_id is None:
        user_id_str = str(user.id)
        if db_manager.use_memory:
            config = await memory_db.find_one("index_configs", {"user_id": user_id_str})
            if not config or not config.get("roots"):
                raise HTTPException(status_code=400, detail="No index roots configured. Please configure roots first.")
        else:
            config = await IndexConfig.find_one(IndexConfig.user_id == user.id)
            if not config or not config.roots:
                raise HTTPException(status_code=400, detail="No index roots configured. Please configure roots first.")
        running = await file_indexer.trigger_index(user.id)
        if running:
            return {"success": True, "message": "Indexing job started.", "job_id": running}
        raise HTTPException(status_code=400, detail="Could not start indexing job.")
    return {"success": True, "message": "Indexing job started.", "job_id": job_id}


@router.get("/index/jobs")
async def get_index_jobs(
    limit: int = Query(10, le=50),
    user: User = Depends(get_current_user)
):
    user_id_str = str(user.id)
    if db_manager.use_memory:
        all_jobs = await memory_db.find("index_jobs", {"user_id": user_id_str})
        all_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        jobs = all_jobs[:limit]
        return {
            "success": True,
            "jobs": [
                {
                    "id": str(j.get("_id")),
                    "status": j.get("status"),
                    "roots": j.get("roots", []),
                    "files_indexed": j.get("files_indexed", 0),
                    "files_updated": j.get("files_updated", 0),
                    "files_removed": j.get("files_removed", 0),
                    "errors": j.get("errors", []),
                    "started_at": j.get("started_at"),
                    "completed_at": j.get("completed_at"),
                    "created_at": j.get("created_at")
                }
                for j in jobs
            ]
        }
    else:
        jobs = await IndexJob.find(IndexJob.user_id == user.id).sort("-created_at").limit(limit).to_list()
        return {
            "success": True,
            "jobs": [
                {
                    "id": str(job.id),
                    "status": job.status,
                    "roots": job.roots,
                    "files_indexed": job.files_indexed,
                    "files_updated": job.files_updated,
                    "files_removed": job.files_removed,
                    "errors": job.errors,
                    "started_at": job.started_at,
                    "completed_at": job.completed_at,
                    "created_at": job.created_at
                }
                for job in jobs
            ]
        }


@router.get("/index/stats")
async def get_index_stats(user: User = Depends(get_current_user)):
    stats = await file_indexer.get_stats(user.id)
    return {"success": True, **stats}
