import os
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import List, Optional
from bson import ObjectId

from app.api.deps import get_current_user, get_user_id
from app.core.database import db_manager
from app.infrastructure.db.models import User, IndexConfig, IndexJob, FileIndex
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


class FileDeleteRequest(BaseModel):
    path: str


def _get_user_roots(user_id_str: str, config_doc) -> List[str]:
    """Extract allowed root paths from an index config."""
    if config_doc is None:
        return []
    if isinstance(config_doc, dict):
        return config_doc.get("roots", [])
    return getattr(config_doc, "roots", []) or []


async def _find_user_roots(user) -> List[str]:
    """Get the user's configured index roots."""
    user_id_str = str(user.id)
    if db_manager.use_memory:
        config = await memory_db.find_one("index_configs", {"user_id": user_id_str})
        return _get_user_roots(user_id_str, config)
    else:
        try:
            config = await IndexConfig.find_one(IndexConfig.user_id == user.id)
        except Exception:
            config = None
        return _get_user_roots(user_id_str, config)


def _normalize_and_validate_path(file_path: str, allowed_roots: List[str]) -> str:
    """Normalize the path and ensure it falls within allowed workspace roots.

    Returns the resolved absolute path if valid.
    Raises HTTPException with a clear error if invalid.
    """
    expanded = os.path.expanduser(os.path.expandvars(file_path))
    normalized = os.path.normpath(expanded)
    resolved = os.path.abspath(normalized)

    if not os.path.isabs(resolved):
        raise HTTPException(status_code=400, detail="Path must be absolute.")

    for root in allowed_roots:
        root_expanded = os.path.expanduser(os.path.expandvars(root))
        root_resolved = os.path.abspath(os.path.normpath(root_expanded))
        if resolved == root_resolved or resolved.startswith(root_resolved + os.sep):
            return resolved

    raise HTTPException(
        status_code=403,
        detail="Path is outside your configured workspace roots. "
               "Add this directory to your index roots first."
    )


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


@router.post("/files/delete")
async def delete_file(
    req: FileDeleteRequest,
    user: User = Depends(get_current_user)
):
    """Delete a single file within the user's configured workspace roots.

    Path handling:
    - Accepts a path in the request body (never in URL).
    - Normalizes and resolves the path before validation.
    - Validates against user's configured index roots.
    - Rejects directories (use OS tools for directory removal).
    - Returns clear errors for all failure modes.
    """
    file_path = req.path.strip()
    if not file_path:
        raise HTTPException(status_code=400, detail="File path is required.")

    # Get user's allowed workspace roots
    allowed_roots = await _find_user_roots(user)
    if not allowed_roots:
        raise HTTPException(
            status_code=400,
            detail="No index roots configured. Configure roots in Settings > Files first."
        )

    # Normalize and validate path stays within workspace
    resolved_path = _normalize_and_validate_path(file_path, allowed_roots)

    # Check existence
    if not os.path.exists(resolved_path):
        raise HTTPException(status_code=404, detail="File not found.")

    # Reject directories
    if os.path.isdir(resolved_path):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete directories through this endpoint. "
                   "Use a terminal command to remove directories."
        )

    # Attempt deletion
    try:
        os.remove(resolved_path)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied. File may be read-only or in use.")
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"File deletion failed: {e}")

    # Remove stale metadata from the file index (best-effort)
    try:
        if db_manager.use_memory:
            await memory_db.delete(
                "file_index",
                {"user_id": str(user.id), "file_path": resolved_path}
            )
        else:
            stale = await FileIndex.find_one(
                FileIndex.user_id == user.id,
                FileIndex.file_path == resolved_path
            )
            if stale:
                await stale.delete()
    except Exception:
        pass  # Metadata cleanup is best-effort

    return {"success": True, "message": f"Deleted: {os.path.basename(resolved_path)}"}
