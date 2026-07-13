import os
import time
import platform
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from app.core.database import db_manager
from app.core.event_bus import event_bus
from app.infrastructure.memory_db import memory_db
from app.services.worker import WorkerPool, TaskQueue, _in_memory_task_statuses, _in_memory_task_queue
from app.services.indexer import file_indexer
from app.recovery.engine import recovery_engine
from app.verification.engine import verification_engine
from app.ai.manager import provider_manager
from app.ai.capabilities import capability_registry

logger = logging.getLogger(__name__)

_start_time = time.monotonic()


class DashboardMetricsService:
    """Collects and returns all dashboard metrics in a single aggregated response, scoped to a single user."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._cache_ts: Dict[str, float] = {}
        self._cache_ttl: float = 5.0

    async def get_metrics(self, user_id: str) -> Dict[str, Any]:
        now = time.monotonic()
        cache_key = user_id
        if cache_key in self._cache and (now - self._cache_ts.get(cache_key, 0)) < self._cache_ttl:
            return self._cache[cache_key]

        metrics = {}
        tasks = [
            self._workflow_metrics(metrics, user_id),
            self._today_metrics(metrics, user_id),
            self._total_metrics(metrics, user_id),
            self._rate_metrics(metrics, user_id),
            self._timing_metrics(metrics, user_id),
            self._verification_metrics(metrics, user_id),
            self._recovery_metrics(metrics),
            self._worker_metrics(metrics),
            self._queue_metrics(metrics),
            self._ai_metrics(metrics),
            self._file_metrics(metrics, user_id),
            self._memory_metrics(metrics, user_id),
            self._system_health(metrics),
            self._system_info(metrics),
            self._recent_activity(metrics, user_id),
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

        self._cache[cache_key] = metrics
        self._cache_ts[cache_key] = now
        return metrics

    def _parse_dt(self, val) -> Optional[datetime]:
        if val is None:
            return None
        if isinstance(val, datetime):
            return val
        if isinstance(val, str):
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                try:
                    return datetime.fromisoformat(val)
                except Exception:
                    return None
        return None

    def _duration_seconds(self, start, end) -> Optional[float]:
        s = self._parse_dt(start)
        e = self._parse_dt(end)
        if s and e:
            return (e - s).total_seconds()
        return None

    async def _get_user_executions(self, user_id: str) -> List[dict]:
        if db_manager.use_memory:
            all_docs = await memory_db.find("workflow_executions")
            return [d for d in all_docs if str(d.get("user_id", "")) == user_id]
        try:
            from app.infrastructure.db.models import WorkflowExecution
            from bson import ObjectId
            docs = await WorkflowExecution.find(
                WorkflowExecution.user_id == ObjectId(user_id)
            ).to_list(length=10000)
            result = []
            for d in docs:
                result.append({
                    "id": str(d.id),
                    "workflow_id": str(d.workflow_id),
                    "user_id": str(d.user_id),
                    "status": d.status,
                    "current_step_index": d.current_step_index,
                    "total_steps": d.total_steps,
                    "started_at": d.started_at.isoformat() if d.started_at else None,
                    "completed_at": d.completed_at.isoformat() if d.completed_at else None,
                    "error_message": d.error_message,
                    "result": d.result,
                    "title": d.title,
                    "description": d.description,
                })
            return result
        except Exception as e:
            logger.error(f"Failed to fetch user executions from MongoDB: {e}")
            return []

    async def _get_user_task_logs(self, user_id: str) -> List[dict]:
        if db_manager.use_memory:
            all_logs = await memory_db.find("task_logs")
            return [l for l in all_logs if str(l.get("user_id", "")) == user_id]
        try:
            from app.infrastructure.db.models import TaskLog
            from bson import ObjectId
            docs = await TaskLog.find(
                TaskLog.user_id == ObjectId(user_id)
            ).to_list(length=10000)
            result = []
            for d in docs:
                result.append({
                    "id": str(d.id),
                    "execution_id": str(d.execution_id),
                    "step_id": d.step_id,
                    "agent_name": d.agent_name,
                    "action": d.action,
                    "status": d.status,
                    "logs": d.logs,
                    "duration_ms": d.duration_ms,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                })
            return result
        except Exception as e:
            logger.error(f"Failed to fetch user task logs: {e}")
            return []

    async def _workflow_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        execs = await self._get_user_executions(user_id)
        status_counts: Dict[str, int] = {}
        for e in execs:
            s = e.get("status", "unknown").lower()
            status_counts[s] = status_counts.get(s, 0) + 1

        m["workflows"] = {
            "running": sum(v for k, v in status_counts.items() if k in ("running", "executing")),
            "queued": status_counts.get("queued", 0),
            "planning": status_counts.get("planning", 0),
            "executing": status_counts.get("executing", 0),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "cancelled": status_counts.get("cancelled", 0),
            "paused": status_counts.get("paused", 0),
            "pending": status_counts.get("pending", 0),
        }

    async def _today_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        execs = await self._get_user_executions(user_id)
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        completed_today = 0
        failed_today = 0
        for e in execs:
            status = e.get("status", "").lower()
            completed_at = self._parse_dt(e.get("completed_at"))
            if completed_at and completed_at >= today_start:
                if status == "completed":
                    completed_today += 1
                elif status == "failed":
                    failed_today += 1
        m["today"] = {"completed": completed_today, "failed": failed_today}

    async def _total_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        execs = await self._get_user_executions(user_id)
        m["total_executions"] = len(execs)

    async def _rate_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        execs = await self._get_user_executions(user_id)
        completed = 0
        failed = 0
        for e in execs:
            s = e.get("status", "").lower()
            if s == "completed":
                completed += 1
            elif s == "failed":
                failed += 1
        total_rateable = completed + failed
        m["success_rate"] = round((completed / total_rateable * 100), 1) if total_rateable > 0 else 0
        m["failure_rate"] = round((failed / total_rateable * 100), 1) if total_rateable > 0 else 0

    async def _timing_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        execs = await self._get_user_executions(user_id)
        durations = []
        for e in execs:
            if e.get("status", "").lower() == "completed":
                d = self._duration_seconds(e.get("started_at"), e.get("completed_at"))
                if d is not None and d >= 0:
                    durations.append(d)

        m["timing"] = {
            "avg_execution_time": round(sum(durations) / len(durations), 1) if durations else 0,
            "fastest_execution": round(min(durations), 1) if durations else 0,
            "slowest_execution": round(max(durations), 1) if durations else 0,
        }

        logs = await self._get_user_task_logs(user_id)
        step_durations = [l.get("duration_ms", 0) for l in logs if l.get("duration_ms")]
        m["timing"]["avg_step_time_ms"] = round(sum(step_durations) / len(step_durations), 0) if step_durations else 0

        total_steps = sum(e.get("total_steps", 0) for e in execs if e.get("total_steps"))
        m["timing"]["avg_steps"] = round(total_steps / len(execs), 1) if execs else 0

    async def _verification_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        logs = await self._get_user_task_logs(user_id)
        verified = sum(1 for l in logs if l.get("status") == "success")
        total = len(logs)
        m["verification"] = {
            "verified_steps": verified,
            "total_steps": total,
            "rate": round((verified / total * 100), 1) if total > 0 else 0,
        }

    async def _recovery_metrics(self, m: Dict[str, Any]) -> None:
        attempts = recovery_engine._attempts
        total_attempts = sum(attempts.values())
        successful = sum(1 for v in attempts.values() if v > 0)
        m["recovery"] = {
            "total_attempts": total_attempts,
            "active_steps": len(attempts),
            "rate": round((successful / len(attempts) * 100), 1) if attempts else 0,
        }

    async def _worker_metrics(self, m: Dict[str, Any]) -> None:
        total_workers = 3
        queue_size = _in_memory_task_queue.qsize() if not db_manager.redis_client else 0
        if db_manager.redis_client:
            try:
                queue_size = await db_manager.redis_client.llen("queue:tasks")
            except Exception:
                queue_size = 0

        statuses = list(_in_memory_task_statuses.values()) if not db_manager.redis_client else []
        busy = sum(1 for s in statuses if s.get("status") == "running")

        m["workers"] = {
            "total": total_workers,
            "busy": busy,
            "idle": total_workers - busy,
            "queue_length": queue_size,
        }

    async def _queue_metrics(self, m: Dict[str, Any]) -> None:
        queue_size = _in_memory_task_queue.qsize() if not db_manager.redis_client else 0
        if db_manager.redis_client:
            try:
                queue_size = await db_manager.redis_client.llen("queue:tasks")
            except Exception:
                queue_size = 0

        m["queue"] = {
            "tasks_waiting": queue_size,
            "avg_wait_seconds": 0,
        }

    async def _ai_metrics(self, m: Dict[str, Any]) -> None:
        try:
            health = await provider_manager.health()
            current_provider = ""
            current_model = ""
            for name, h in health.items():
                if h.available:
                    current_provider = name
                    current_model = h.model or ""
                    break

            provider_metrics = provider_manager.get_metrics()
            total_requests = sum(p.total_requests for p in provider_metrics.values())
            total_tokens_in = sum(p.total_tokens_input for p in provider_metrics.values())
            total_tokens_out = sum(p.total_tokens_output for p in provider_metrics.values())
            total_latency = sum(p.total_latency_ms for p in provider_metrics.values())
            avg_response_ms = round(total_latency / total_requests, 0) if total_requests > 0 else 0

            m["ai"] = {
                "current_provider": current_provider,
                "current_model": current_model,
                "total_requests": total_requests,
                "total_tokens_input": total_tokens_in,
                "total_tokens_output": total_tokens_out,
                "total_tokens": total_tokens_in + total_tokens_out,
                "avg_response_ms": avg_response_ms,
                "provider_count": len(provider_metrics),
                "providers": [
                    {
                        "name": p.provider,
                        "model": p.model,
                        "requests": p.total_requests,
                        "errors": p.total_errors,
                        "tokens_in": p.total_tokens_input,
                        "tokens_out": p.total_tokens_output,
                    }
                    for p in provider_metrics.values()
                ],
            }
        except Exception as e:
            m["ai"] = {"error": str(e), "current_provider": "", "current_model": ""}

    async def _file_metrics(self, m: Dict[str, Any], user_id: str = "") -> None:
        try:
            if db_manager.use_memory:
                all_files = await memory_db.find("file_index")
                files = [f for f in all_files if str(f.get("user_id", "")) == user_id]
            else:
                from app.infrastructure.db.models import FileIndex, PydanticObjectId
                from bson import ObjectId
                try:
                    uid = ObjectId(user_id) if user_id else None
                except Exception:
                    uid = None
                if uid:
                    files_docs = await FileIndex.find(FileIndex.user_id == uid).to_list(length=100000)
                else:
                    files_docs = await FileIndex.find().to_list(length=100000)
                files = [{"file_path": f.file_path, "file_name": f.file_name, "extension": f.extension} for f in files_docs]
            m["files"] = {
                "indexed_files": len(files),
                "indexed_directories": len(set(os.path.dirname(f.get("file_path", "")) for f in files if f.get("file_path"))),
            }
        except Exception as e:
            m["files"] = {"indexed_files": 0, "indexed_directories": 0, "error": str(e)}

    async def _memory_metrics(self, m: Dict[str, Any], user_id: str) -> None:
        try:
            if db_manager.use_memory:
                all_memories = await memory_db.find("memory_store")
                memories = [mm for mm in all_memories if str(mm.get("user_id", "")) == user_id]
            else:
                from app.infrastructure.db.models import MemoryStore
                from bson import ObjectId
                mem_docs = await MemoryStore.find(
                    MemoryStore.user_id == ObjectId(user_id)
                ).to_list(length=10000)
                memories = [{"key": mm.key, "type": mm.type} for mm in mem_docs]
            m["memory"] = {
                "total_entries": len(memories),
                "types": {},
            }
            for mem in memories:
                t = mem.get("type", "unknown")
                m["memory"]["types"][t] = m["memory"]["types"].get(t, 0) + 1
        except Exception as e:
            m["memory"] = {"total_entries": 0, "error": str(e)}

    async def _system_health(self, m: Dict[str, Any]) -> None:
        health_checks = {}

        health_checks["backend"] = {"status": "healthy", "latency_ms": 0}

        try:
            start = time.monotonic()
            if db_manager.use_memory:
                health_checks["mongodb"] = {"status": "unavailable", "latency_ms": 0, "note": "Using in-memory storage"}
            else:
                await asyncio.wait_for(db_manager.db.command("ping"), timeout=3.0)
                health_checks["mongodb"] = {"status": "healthy", "latency_ms": round((time.monotonic() - start) * 1000, 0)}
        except Exception as e:
            health_checks["mongodb"] = {"status": "unavailable", "error": str(e)}

        try:
            if db_manager.redis_client:
                start = time.monotonic()
                await asyncio.wait_for(db_manager.redis_client.ping(), timeout=3.0)
                health_checks["redis"] = {"status": "healthy", "latency_ms": round((time.monotonic() - start) * 1000, 0)}
            else:
                health_checks["redis"] = {"status": "unavailable", "note": "Using in-memory event bus"}
        except Exception as e:
            health_checks["redis"] = {"status": "unavailable", "error": str(e)}

        try:
            ai_health = await provider_manager.health()
            available = any(h.available for h in ai_health.values())
            health_checks["ai_provider"] = {"status": "healthy" if available else "unavailable", "providers": len(ai_health)}
        except Exception as e:
            health_checks["ai_provider"] = {"status": "unavailable", "error": str(e)}

        health_checks["worker_pool"] = {"status": "healthy", "workers": 3}
        health_checks["event_bus"] = {"status": "healthy" if event_bus._is_listening else "stopped"}
        health_checks["file_indexer"] = {"status": "running" if file_indexer._running else "stopped"}

        m["system_health"] = health_checks

    async def _system_info(self, m: Dict[str, Any]) -> None:
        uptime_seconds = time.monotonic() - _start_time
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        uptime_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
        except ImportError:
            cpu_percent = 0
            mem = None
            disk = None

        m["system_info"] = {
            "os": f"{platform.system()} {platform.release()}",
            "python_version": platform.python_version(),
            "cpu_percent": cpu_percent,
            "ram_total_gb": round(mem.total / (1024**3), 1) if mem else 0,
            "ram_used_gb": round(mem.used / (1024**3), 1) if mem else 0,
            "ram_percent": mem.percent if mem else 0,
            "disk_total_gb": round(disk.total / (1024**3), 1) if disk else 0,
            "disk_used_gb": round(disk.used / (1024**3), 1) if disk else 0,
            "disk_percent": round(disk.percent, 1) if disk else 0,
            "uptime": uptime_str,
            "uptime_seconds": round(uptime_seconds, 0),
        }

    async def _recent_activity(self, m: Dict[str, Any], user_id: str) -> None:
        execs = await self._get_user_executions(user_id)
        execs.sort(key=lambda e: e.get("started_at") or "", reverse=True)
        recent = execs[:20]

        m["recent_activity"] = []
        for e in recent:
            duration = self._duration_seconds(e.get("started_at"), e.get("completed_at"))
            m["recent_activity"].append({
                "id": e.get("id", ""),
                "title": e.get("title") or e.get("description", "Untitled"),
                "status": e.get("status", "unknown"),
                "started_at": e.get("started_at"),
                "completed_at": e.get("completed_at"),
                "duration_seconds": round(duration, 1) if duration else None,
                "total_steps": e.get("total_steps", 0),
                "current_step": e.get("current_step_index", 0),
                "error": e.get("error_message"),
            })


dashboard_service = DashboardMetricsService()
