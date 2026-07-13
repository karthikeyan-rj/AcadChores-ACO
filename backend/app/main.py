from typing import Dict, List, Any
import logging
import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from jose import jwt, JWTError

from app.core.config import settings
from app.core.database import db_manager
from app.core.event_bus import event_bus, SystemEvent
from app.core.security import ALGORITHM
from app.services.worker import WorkerPool
from app.services.agent_dispatcher import agent_manager
from app.services.indexer import file_indexer
from app.ai.factory import provider_factory
from app.ai.service import llm_service
from app.ai.capabilities import capability_registry
from app.api.v1.api import api_router

# Configure logging system
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize background worker pool with agent dispatcher
worker_pool = WorkerPool(agent_manager=agent_manager)

# Event buffer: execution_id -> list of events (capped at 100 per execution)
_event_buffer: Dict[str, list] = defaultdict(list)
_event_buffer_max = 100

# Permission event buffer: stores recent permission.request events so they can be
# replayed to WebSocket clients that connect after the event was published.
# This fixes the race condition where the first permission request fires before
# the WebSocket event_forwarder is subscribed.
_permission_buffer: list = []
_permission_buffer_max = 20

async def _buffer_events(event: SystemEvent):
    exec_id = event.payload.get("execution_id")
    if exec_id:
        _event_buffer[exec_id].append(event.model_dump())
        if len(_event_buffer[exec_id]) > _event_buffer_max:
            _event_buffer[exec_id] = _event_buffer[exec_id][-_event_buffer_max:]

    # Buffer permission.request events for replay to late-connecting WebSockets
    if event.topic == "permission.request":
        _permission_buffer.append(event.model_dump())
        if len(_permission_buffer) > _permission_buffer_max:
            _permission_buffer.pop(0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle routines
    logger.info("Starting up ACO FastAPI application...")
    
    # 1. Connect MongoDB & Redis connections
    await db_manager.initialize()
    
    # 2. Start Event Bus listener
    await event_bus.start_listening()
    
    # 2a. Initialize AI providers (auto-discover from providers folder)
    await provider_factory.discover_and_register()
    health_results = await llm_service.health()
    for name, health in health_results.items():
        if health.available:
            logger.info(f"AI Provider '{name}' is available [model={health.model}]")
        else:
            logger.warning(f"AI Provider '{name}' unavailable: {health.error}")
    
    # 2aa. Initialize capability registry with default agent capabilities
    capability_registry.initialize_defaults()
    logger.info(f"Capability registry initialized with {len(capability_registry.all_agents())} agents, {len(capability_registry.all_actions())} total actions")
    
    # 2b. Subscribe event buffer for all execution-related topics + permission.request
    # permission.request is pre-subscribed so Redis PubSub picks it up immediately
    # without waiting for a WebSocket to register the handler
    for topic in ["task.started", "task.progress", "task.completed", "task.failed",
                   "verification.failed", "workflow.state_change", "permission.request"]:
        event_bus.subscribe(topic, _buffer_events)
    
    # 3. Start background Worker Pool (3 concurrency workers)
    await worker_pool.start(num_workers=3)
    
    # 4. Start background directory file indexing crawl loop
    file_indexer.start()
    
    yield
    
    # Shutdown lifecycle routines
    logger.info("Shutting down ACO FastAPI application...")
    
    # 1. Stop background services
    file_indexer.stop()
    await worker_pool.stop()
    await event_bus.stop_listening()
    
    # 2. Cleanup browser contexts
    await agent_manager.cleanup()
    
    # 3. Close database connections
    await db_manager.close()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

# Configure CORS for Next.js and Electron interfaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "project": settings.PROJECT_NAME}


@app.websocket("/ws/executions/{execution_id}")
async def ws_execution_monitor(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint enabling live updates (screen, step progress, permissions)
    to stream directly to Electron UI dashboard client.
    Only streams events belonging to the authenticated user.
    """
    # Optional token verification from query parameters
    token = websocket.query_params.get("token")
    user = None
    if token:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            email = payload.get("sub")
            if email:
                from app.infrastructure.db.models import User
                user = await User.find_one(User.email == email)
        except JWTError:
            await websocket.close(code=1008)  # Policy violation
            return

    await websocket.accept()
    logger.info(f"WebSocket client connected to monitor execution: {execution_id}")

    # Replay any buffered events that fired before the WebSocket connected
    buffered = _event_buffer.pop(execution_id, [])
    replayed = 0
    for event_data in buffered:
        # Filter: only replay events if we can verify ownership
        event_exec_id = event_data.get("payload", {}).get("execution_id", "")
        if event_exec_id == execution_id:
            if user:
                # Authenticated: verify the execution belongs to this user
                from app.services.workflow_engine import _find_exec
                exec_doc = await _find_exec(execution_id)
                if exec_doc and str(exec_doc.get("user_id", "")) == str(user.id):
                    try:
                        await websocket.send_json(event_data)
                        replayed += 1
                    except Exception:
                        pass
            else:
                # No auth — replay all matching events (backward compatibility)
                try:
                    await websocket.send_json(event_data)
                    replayed += 1
                except Exception:
                    pass
    if replayed > 0:
        logger.info(f"Replayed {replayed} buffered events for execution {execution_id}")

    # Channel event forwarding queue
    event_queue = asyncio.Queue()

    # Define Event Bus callback routing — filtered by authenticated user
    async def event_forwarder(event: SystemEvent):
        # Filter events matching this execution ID
        payload_exec_id = event.payload.get("execution_id")

        # Permission requests don't carry execution_id — forward them to all connected clients
        # for this execution since they're always for the current user's active session
        is_permission = event.topic == "permission.request"

        if is_permission or payload_exec_id == execution_id:
            logger.debug(f"event_forwarder: received {event.topic} for exec {execution_id}")
            # If we have an authenticated user, verify the execution belongs to them
            if user:
                if not is_permission:
                    from app.services.workflow_engine import _find_exec
                    exec_doc = await _find_exec(execution_id)
                    if exec_doc and str(exec_doc.get("user_id", "")) != str(user.id):
                        return
            try:
                await event_queue.put(event.model_dump())
            except Exception:
                pass

    # Subscribe to related Topics — track for cleanup
    forwarder_topics = [
        "workflow.state_change", "task.progress", "task.started",
        "task.completed", "task.failed", "permission.request", "verification.failed",
    ]
    for topic in forwarder_topics:
        event_bus.subscribe(topic, event_forwarder)

    # Replay any buffered permission.request events that fired before this WebSocket connected.
    # This fixes the race condition where the first permission request fires while the worker
    # starts executing, before the WebSocket event_forwarder is subscribed.
    if _permission_buffer:
        pending_perms = list(_permission_buffer)
        _permission_buffer.clear()
        for perm_event in pending_perms:
            try:
                await websocket.send_json(perm_event)
                logger.info(f"Replayed buffered permission event {perm_event.get('payload', {}).get('request_id', '?')} to WebSocket")
            except Exception:
                pass

    # Listen loop forwarding events over WebSocket channel
    try:
        while True:
            # Non-blocking pop from event queue with 0.1s timeout
            try:
                event_data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                await websocket.send_json(event_data)
            except asyncio.TimeoutError:
                pass
            
            # Simple heartbeat ping from client check
            # Keeps websocket alive and checks for disconnection
            try:
                # Receive message if client sends anything (e.g. ping)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected for execution: {execution_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket execution stream: {e}")
    finally:
        # Cleanup: unsubscribe all event_forwarder handlers to prevent memory leaks
        for topic in forwarder_topics:
            event_bus.unsubscribe(topic, event_forwarder)
        logger.info(f"Cleaned up {len(forwarder_topics)} event subscriptions for execution: {execution_id}")
