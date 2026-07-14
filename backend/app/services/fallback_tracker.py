import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


async def record_fallback_usage(
    user_id: str,
    provider: str,
    model: str,
    fallback_reason: str,
    planner_source: str,
    local_attempts: int = 0,
    quality_score: float = 0.0,
    success: bool = True,
    tokens_input: int = 0,
    tokens_output: int = 0,
    latency_ms: float = 0.0,
) -> None:
    try:
        from app.core.database import get_database
        from motor.motor_asyncio import AsyncIOMotorDatabase

        db: AsyncIOMotorDatabase = await get_database()
        doc = {
            "user_id": str(user_id),
            "provider": provider,
            "model": model,
            "timestamp": datetime.utcnow(),
            "fallback_reason": fallback_reason,
            "planner_source": planner_source,
            "local_attempts": local_attempts,
            "quality_score": quality_score,
            "success": success,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms,
        }
        await db.fallback_usage.insert_one(doc)
    except Exception as e:
        logger.error(f"Failed to record fallback usage: {e}")


async def get_daily_usage_count(user_id: str) -> int:
    try:
        from app.core.database import get_database
        from motor.motor_asyncio import AsyncIOMotorDatabase

        db: AsyncIOMotorDatabase = await get_database()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        count = await db.fallback_usage.count_documents({
            "user_id": str(user_id),
            "timestamp": {"$gte": today_start},
        })
        return count
    except Exception as e:
        logger.error(f"Failed to get daily usage count: {e}")
        return 0


async def get_usage_stats(user_id: str, days: int = 30) -> Dict[str, Any]:
    try:
        from app.core.database import get_database
        from motor.motor_asyncio import AsyncIOMotorDatabase

        db: AsyncIOMotorDatabase = await get_database()
        since = datetime.utcnow() - timedelta(days=days)
        cursor = db.fallback_usage.find({"user_id": str(user_id), "timestamp": {"$gte": since}})
        total_calls = 0
        success_calls = 0
        total_tokens_in = 0
        total_tokens_out = 0
        providers_used = set()
        async for doc in cursor:
            total_calls += 1
            if doc.get("success"):
                success_calls += 1
            total_tokens_in += doc.get("tokens_input", 0)
            total_tokens_out += doc.get("tokens_output", 0)
            providers_used.add(doc.get("provider", ""))
        return {
            "total_calls": total_calls,
            "success_calls": success_calls,
            "failure_calls": total_calls - success_calls,
            "success_rate": round(success_calls / total_calls * 100, 1) if total_calls > 0 else 0,
            "total_tokens_input": total_tokens_in,
            "total_tokens_output": total_tokens_out,
            "providers_used": list(providers_used),
            "period_days": days,
        }
    except Exception as e:
        logger.error(f"Failed to get usage stats: {e}")
        return {"total_calls": 0, "success_calls": 0, "failure_calls": 0, "success_rate": 0}
