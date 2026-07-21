import json
import logging
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from bson import ObjectId
from app.core.database import db_manager
from app.infrastructure.memory_db import memory_db
from app.core.event_bus import event_bus
from app.infrastructure.db.models import WorkflowExecution

logger = logging.getLogger(__name__)

# Global in-memory checkpoint fallbacks
_in_memory_states: Dict[str, str] = {}
_in_memory_state_details: Dict[str, str] = {}

# Maximum entries before cleanup (1000)
_MAX_IN_MEMORY_ENTRIES = 1000


def _cleanup_in_memory_states():
    """Evict oldest entries if the in-memory cache grows too large."""
    if len(_in_memory_states) > _MAX_IN_MEMORY_ENTRIES:
        # Remove the oldest half of entries (by insertion order in dict)
        keys = list(_in_memory_states.keys())
        for k in keys[: len(keys) // 2]:
            _in_memory_states.pop(k, None)
            _in_memory_state_details.pop(k, None)

class WorkflowState(str, Enum):
    IDLE = "Idle"
    PLANNING = "Planning"
    EXECUTING = "Executing"
    WAITING = "Waiting"
    RETRY = "Retry"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"
    STOPPING = "Stopping"

# Valid transitions map
VALID_TRANSITIONS = {
    WorkflowState.IDLE: [WorkflowState.PLANNING, WorkflowState.CANCELLED],
    WorkflowState.PLANNING: [WorkflowState.EXECUTING, WorkflowState.FAILED, WorkflowState.CANCELLED],
    WorkflowState.EXECUTING: [WorkflowState.WAITING, WorkflowState.RETRY, WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED, WorkflowState.STOPPING],
    WorkflowState.WAITING: [WorkflowState.EXECUTING, WorkflowState.FAILED, WorkflowState.CANCELLED],
    WorkflowState.RETRY: [WorkflowState.EXECUTING, WorkflowState.FAILED, WorkflowState.CANCELLED],
    WorkflowState.STOPPING: [WorkflowState.CANCELLED, WorkflowState.FAILED],
    WorkflowState.COMPLETED: [],
    WorkflowState.FAILED: [],
    WorkflowState.CANCELLED: []
}

class WorkflowStateMachine:
    @staticmethod
    async def get_state(execution_id: str) -> Optional[WorkflowState]:
        """Gets current state from Redis cache, falling back to in-memory dict or MongoDB."""
        redis = db_manager.redis_client
        if redis:
            cached_state = await redis.get(f"state:workflow:{execution_id}")
            if cached_state:
                return WorkflowState(cached_state)
        else:
            cached_state = _in_memory_states.get(execution_id)
            if cached_state:
                return WorkflowState(cached_state)

        # Fallback to memory_db then MongoDB
        doc = await memory_db.find_one("workflow_executions", {"_id": ObjectId(execution_id)})
        if doc and doc.get("status"):
            return WorkflowState(doc["status"])
        if not db_manager.use_memory:
            try:
                execution = await WorkflowExecution.get(execution_id)
                if execution:
                    return WorkflowState(execution.status)
            except Exception:
                pass
        return None

    @staticmethod
    async def get_status(execution_id: str) -> Optional[str]:
        """Returns the status string for an execution, or None if not found."""
        state = await WorkflowStateMachine.get_state(execution_id)
        return state.value if state else None

    @staticmethod
    async def transition_to(
        execution_id: str,
        new_state: WorkflowState,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Attempts to transition the execution to a new state.
        Validates transition, writes to Redis (or In-Memory checkpoint), updates MongoDB, and publishes an event.
        """
        current_state = await WorkflowStateMachine.get_state(execution_id)
        if not current_state:
            current_state = WorkflowState.IDLE

        # Validate transition (skip if it's the first state or error override)
        if current_state in VALID_TRANSITIONS and new_state not in VALID_TRANSITIONS[current_state]:
            logger.warning(
                f"Invalid state transition attempted: {current_state} -> {new_state} for execution {execution_id}"
            )
            return False

        logger.info(f"Transitioning execution {execution_id} from {current_state} to {new_state}")

        state_data = {
            "state": new_state.value,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }

        # 1. Update Redis or In-Memory fallback (hot checkpoint cache)
        redis = db_manager.redis_client
        if redis:
            await redis.set(f"state:workflow:{execution_id}", new_state.value)
            await redis.set(f"state:workflow:details:{execution_id}", json.dumps(state_data))
        else:
            _in_memory_states[execution_id] = new_state.value
            _in_memory_state_details[execution_id] = json.dumps(state_data)
            _cleanup_in_memory_states()

        # 2. Update MongoDB or In-Memory
        if db_manager.use_memory:
            update = {"status": new_state.value}
            if error_message:
                update["error_message"] = error_message
            if new_state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
                update["completed_at"] = datetime.now(timezone.utc).isoformat()
            if new_state == WorkflowState.CANCELLED:
                update["stopped_at"] = datetime.now(timezone.utc).isoformat()
            if new_state == WorkflowState.FAILED:
                update["result_type"] = "failed"
            await memory_db.update("workflow_executions", {"_id": ObjectId(execution_id)}, update)
        else:
            execution = await WorkflowExecution.get(execution_id)
            if execution:
                execution.status = new_state.value
                execution.updated_at = datetime.now(timezone.utc)
                if error_message:
                    execution.error_message = error_message
                if new_state in [WorkflowState.COMPLETED, WorkflowState.FAILED, WorkflowState.CANCELLED]:
                    execution.completed_at = datetime.now(timezone.utc)
                if new_state == WorkflowState.CANCELLED:
                    execution.stopped_at = datetime.now(timezone.utc)
                if new_state == WorkflowState.FAILED:
                    execution.result_type = "failed"
                await execution.save()

        # 3. Publish update event to Event Bus
        await event_bus.publish(
            topic="workflow.state_change",
            sender="WorkflowStateMachine",
            payload={
                "execution_id": execution_id,
                "old_state": current_state.value,
                "new_state": new_state.value,
                "error_message": error_message,
                "metadata": metadata or {}
            }
        )
        return True

    @staticmethod
    async def recover_state(execution_id: str) -> Optional[Dict[str, Any]]:
        """Loads state checkpoint to resume work after a crash or restart."""
        redis = db_manager.redis_client
        if redis:
            details_str = await redis.get(f"state:workflow:details:{execution_id}")
        else:
            details_str = _in_memory_state_details.get(execution_id)

        if details_str:
            return json.loads(details_str)
        return None
