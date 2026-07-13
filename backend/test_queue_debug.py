"""
Standalone test script to verify the in-memory task queue works correctly.
This completely bypasses FastAPI/uvicorn to eliminate process boundary issues.
"""
import asyncio
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ["PORT"] = "8001"

async def main():
    # Patch db_manager to force in-memory mode BEFORE importing anything that uses it
    from app.core import database
    database.db_manager.use_memory = True
    database.db_manager.redis_client = None

    from app.services.worker import _in_memory_task_queue, TaskQueue, WorkerPool
    from app.services.agent_dispatcher import agent_manager

    print(f"MAIN: queue object id = {id(_in_memory_task_queue)}")
    print(f"MAIN: queue qsize before = {_in_memory_task_queue.qsize()}")

    # Start the WorkerPool
    pool = WorkerPool(agent_manager=agent_manager)
    await pool.start(num_workers=2)
    print("MAIN: WorkerPool started")

    await asyncio.sleep(1)

    step_payload = {
        "agent_type": "browser",
        "action": "navigate",
        "parameters": {"url": "https://google.com"},
        "step_id": "step-1"
    }

    print(f"MAIN: About to enqueue task... queue id = {id(_in_memory_task_queue)}")
    task_id = await TaskQueue.enqueue("exec-123", step_payload)
    print(f"MAIN: Enqueued task {task_id}, qsize now = {_in_memory_task_queue.qsize()}")

    # Wait for worker to process
    await asyncio.sleep(5)

    print(f"MAIN: After 5s, qsize = {_in_memory_task_queue.qsize()}")
    print(f"MAIN: Task status = {await TaskQueue.get_status(task_id)}")

    await pool.stop()
    print("MAIN: Done")

if __name__ == "__main__":
    asyncio.run(main())