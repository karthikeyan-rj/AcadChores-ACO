import os
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from bson import ObjectId

from app.core.config import settings
from app.core.database import db_manager
from app.infrastructure.db.models import FileIndex, IndexConfig, IndexJob, PydanticObjectId
from app.infrastructure.memory_db import memory_db

logger = logging.getLogger(__name__)


class FileIndexer:
    def __init__(self):
        self._indexing_tasks: Dict[str, asyncio.Task] = {}
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        asyncio.create_task(self._index_loop())
        logger.info("File Indexer background service started.")

    def stop(self) -> None:
        self._running = False
        for task in self._indexing_tasks.values():
            task.cancel()
        self._indexing_tasks.clear()
        logger.info("File Indexer background service stopped.")

    async def _index_loop(self) -> None:
        while self._running:
            try:
                if db_manager.use_memory:
                    configs = await memory_db.find("index_configs", {"enabled": True})
                else:
                    configs = await IndexConfig.find(IndexConfig.enabled == True).to_list()
                for config_data in configs:
                    if db_manager.use_memory:
                        user_id_str = config_data.get("user_id", "")
                    else:
                        user_id_str = str(config_data.user_id)
                    if user_id_str in self._indexing_tasks and not self._indexing_tasks[user_id_str].done():
                        continue
                    task = asyncio.create_task(self._index_for_user(config_data))
                    self._indexing_tasks[user_id_str] = task
                await asyncio.sleep(settings.INDEX_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in File Indexer loop: {e}")
                await asyncio.sleep(60)

    async def _index_for_user(self, config_data: Any) -> None:
        if db_manager.use_memory:
            user_id_str = config_data.get("user_id", "")
            user_oid = ObjectId(user_id_str) if user_id_str else ObjectId()
            roots = config_data.get("roots", settings.INDEXER_ROOTS)
            max_size_mb = config_data.get("max_file_size_mb", 100)
            exclude_dirs = config_data.get("exclude_dirs", [])
            exclude_extensions = config_data.get("exclude_extensions", [])
        else:
            user_id_str = str(config_data.user_id)
            user_oid = config_data.user_id
            roots = config_data.roots or settings.INDEXER_ROOTS
            max_size_mb = config_data.max_file_size_mb or 100
            exclude_dirs = config_data.exclude_dirs or []
            exclude_extensions = config_data.exclude_extensions or []

        max_size_bytes = max_size_mb * 1024 * 1024

        job_data = {
            "user_id": user_oid,
            "status": "running",
            "roots": roots,
            "files_indexed": 0,
            "files_updated": 0,
            "files_removed": 0,
            "errors": [],
            "started_at": datetime.utcnow().isoformat() if db_manager.use_memory else datetime.utcnow(),
        }

        if db_manager.use_memory:
            job_id = await memory_db.insert("index_jobs", job_data)
        else:
            job = IndexJob(user_id=user_oid, status="running", roots=roots, started_at=datetime.utcnow())
            await job.insert()
            job_id = job.id

        indexed_paths: set = set()
        errors: List[str] = []

        try:
            loop = asyncio.get_running_loop()
            for root in roots:
                if not os.path.exists(root):
                    continue
                try:
                    files_meta = await loop.run_in_executor(
                        None, self._scan_directory, root, exclude_dirs,
                        exclude_extensions, max_size_bytes
                    )
                    for fm in files_meta:
                        indexed_paths.add(fm["file_path"])
                        if db_manager.use_memory:
                            existing = None
                            for doc in memory_db._in_memory_collections.get("file_index", {}).values():
                                if doc.get("file_path") == fm["file_path"] and str(doc.get("user_id")) == user_id_str:
                                    existing = doc
                                    break
                            if existing:
                                if existing.get("modified_at") != fm["modified_at"].isoformat():
                                    existing["file_name"] = fm["file_name"]
                                    existing["extension"] = fm["extension"]
                                    existing["size_bytes"] = fm["size_bytes"]
                                    existing["modified_at"] = fm["modified_at"].isoformat()
                                    existing["last_indexed_at"] = datetime.utcnow().isoformat()
                                    job_data["files_updated"] += 1
                            else:
                                fm["user_id"] = str(user_oid)
                                fm["modified_at"] = fm["modified_at"].isoformat()
                                fm["last_indexed_at"] = datetime.utcnow().isoformat()
                                await memory_db.insert("file_index", fm)
                                job_data["files_indexed"] += 1
                        else:
                            existing = await FileIndex.find_one(
                                FileIndex.file_path == fm["file_path"],
                                FileIndex.user_id == user_oid
                            )
                            if existing:
                                if existing.modified_at != fm["modified_at"]:
                                    existing.file_name = fm["file_name"]
                                    existing.extension = fm["extension"]
                                    existing.size_bytes = fm["size_bytes"]
                                    existing.modified_at = fm["modified_at"]
                                    existing.last_indexed_at = datetime.utcnow()
                                    await existing.save()
                                    job_data["files_updated"] += 1
                            else:
                                file_doc = FileIndex(
                                    file_path=fm["file_path"],
                                    file_name=fm["file_name"],
                                    extension=fm["extension"],
                                    size_bytes=fm["size_bytes"],
                                    modified_at=fm["modified_at"],
                                    user_id=user_oid,
                                    last_indexed_at=datetime.utcnow()
                                )
                                await file_doc.insert()
                                job_data["files_indexed"] += 1
                except Exception as e:
                    errors.append(f"Error scanning {root}: {e}")
                    logger.error(f"Error scanning {root} for user {user_id_str}: {e}")

            if db_manager.use_memory:
                user_files = [
                    doc for doc in memory_db._in_memory_collections.get("file_index", {}).values()
                    if str(doc.get("user_id")) == user_id_str
                ]
                for uf in user_files:
                    if uf.get("file_path") not in indexed_paths:
                        memory_db._in_memory_collections["file_index"].pop(uf.get("_id"), None)
                        job_data["files_removed"] += 1
            else:
                existing_files = await FileIndex.find(FileIndex.user_id == user_oid).to_list()
                for ef in existing_files:
                    if ef.file_path not in indexed_paths:
                        await ef.delete()
                        job_data["files_removed"] += 1

            job_data["status"] = "completed"
            job_data["errors"] = errors
            job_data["completed_at"] = datetime.utcnow().isoformat() if db_manager.use_memory else datetime.utcnow()
        except Exception as e:
            job_data["status"] = "failed"
            job_data["errors"] = errors + [str(e)]
            job_data["completed_at"] = datetime.utcnow().isoformat() if db_manager.use_memory else datetime.utcnow()
            logger.error(f"Index job failed for user {user_id_str}: {e}")

        if db_manager.use_memory:
            await memory_db.update("index_jobs", {"_id": job_id}, {
                "status": job_data["status"],
                "files_indexed": job_data["files_indexed"],
                "files_updated": job_data["files_updated"],
                "files_removed": job_data["files_removed"],
                "errors": job_data["errors"],
                "completed_at": job_data["completed_at"]
            })
        else:
            job_doc = await IndexJob.find_one(IndexJob.id == job_id)
            if job_doc:
                job_doc.status = job_data["status"]
                job_doc.files_indexed = job_data["files_indexed"]
                job_doc.files_updated = job_data["files_updated"]
                job_doc.files_removed = job_data["files_removed"]
                job_doc.errors = job_data["errors"]
                job_doc.completed_at = job_data["completed_at"]
                await job_doc.save()

        logger.info(
            f"Index job {job_id} for user {user_id_str}: "
            f"indexed={job_data['files_indexed']}, updated={job_data['files_updated']}, "
            f"removed={job_data['files_removed']}, errors={len(job_data['errors'])}"
        )

    @staticmethod
    def _scan_directory(
        root_dir: str,
        exclude_dirs: List[str],
        exclude_extensions: List[str],
        max_size_bytes: int
    ) -> List[Dict[str, Any]]:
        files_list = []
        exclude_dirs_lower = [x.lower() for x in exclude_dirs]
        exclude_ext_lower = [x.lower() for x in exclude_extensions]
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [
                d for d in dirs
                if not d.startswith('.') and d.lower() not in exclude_dirs_lower
            ]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in exclude_ext_lower:
                    continue
                full_path = os.path.join(root, f)
                try:
                    stat = os.stat(full_path)
                    if stat.st_size > max_size_bytes:
                        continue
                    files_list.append({
                        "file_path": full_path,
                        "file_name": f,
                        "extension": ext,
                        "size_bytes": stat.st_size,
                        "modified_at": datetime.fromtimestamp(stat.st_mtime)
                    })
                except (PermissionError, FileNotFoundError):
                    continue
                if len(files_list) >= 10000:
                    break
            if len(files_list) >= 10000:
                break
        return files_list

    async def search(self, query: str, user_id: PydanticObjectId, limit: int = 50) -> List[Dict[str, Any]]:
        user_id_str = str(user_id)
        if db_manager.use_memory:
            results = []
            for doc in memory_db._in_memory_collections.get("file_index", {}).values():
                if str(doc.get("user_id")) == user_id_str and query.lower() in doc.get("file_name", "").lower():
                    results.append(doc)
                    if len(results) >= limit:
                        break
            return results
        else:
            docs = await FileIndex.find(
                FileIndex.user_id == user_id,
                {"file_name": {"$regex": query, "$options": "i"}}
            ).limit(limit).to_list()
            return [
                {
                    "file_name": d.file_name,
                    "file_path": d.file_path,
                    "extension": d.extension,
                    "size_bytes": d.size_bytes,
                    "modified_at": d.modified_at
                }
                for d in docs
            ]

    async def trigger_index(self, user_id: PydanticObjectId) -> Optional[str]:
        user_id_str = str(user_id)
        if db_manager.use_memory:
            config = await memory_db.find_one("index_configs", {"user_id": user_id_str})
        else:
            config = await IndexConfig.find_one(IndexConfig.user_id == user_id)
        if not config:
            return None
        if user_id_str in self._indexing_tasks and not self._indexing_tasks[user_id_str].done():
            return None
        task = asyncio.create_task(self._index_for_user(config))
        self._indexing_tasks[user_id_str] = task
        await asyncio.sleep(0.2)
        if db_manager.use_memory:
            for doc in memory_db._in_memory_collections.get("index_jobs", {}).values():
                if str(doc.get("user_id")) == user_id_str and doc.get("status") == "running":
                    return str(doc.get("_id"))
        else:
            job = await IndexJob.find_one(IndexJob.user_id == user_id, IndexJob.status == "running")
            if job:
                return str(job.id)
        return None

    async def get_stats(self, user_id: PydanticObjectId) -> Dict[str, Any]:
        user_id_str = str(user_id)
        if db_manager.use_memory:
            user_files = [
                doc for doc in memory_db._in_memory_collections.get("file_index", {}).values()
                if str(doc.get("user_id")) == user_id_str
            ]
            total_files = len(user_files)
            ext_map: Dict[str, Dict[str, int]] = {}
            total_size = 0
            for f in user_files:
                ext = f.get("extension", "none")
                size = f.get("size_bytes", 0)
                total_size += size
                if ext not in ext_map:
                    ext_map[ext] = {"count": 0, "total_size": 0}
                ext_map[ext]["count"] += 1
                ext_map[ext]["total_size"] += size
            top_extensions = sorted(
                [{"extension": k, **v} for k, v in ext_map.items()],
                key=lambda x: x["count"], reverse=True
            )[:10]
            return {"total_files": total_files, "total_size_bytes": total_size, "top_extensions": top_extensions}
        else:
            total_files = await FileIndex.find(FileIndex.user_id == user_id).count()
            try:
                ext_pipeline = [
                    {"$match": {"user_id": str(user_id)}},
                    {"$group": {"_id": "$extension", "count": {"$sum": 1}, "total_size": {"$sum": "$size_bytes"}}},
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
                ext_results = await db_manager.db.file_index.aggregate(ext_pipeline).to_list(10)
            except Exception:
                ext_results = []
            total_size = sum(r.get("total_size", 0) for r in ext_results)
            top_extensions = [
                {"extension": r["_id"] or "none", "count": r["count"], "total_size": r["total_size"]}
                for r in ext_results
            ]
            return {"total_files": total_files, "total_size_bytes": total_size, "top_extensions": top_extensions}


file_indexer = FileIndexer()
