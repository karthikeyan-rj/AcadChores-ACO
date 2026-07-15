from typing import Dict, List, Any
import logging
import asyncio
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

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
from app.core.rate_limit import limiter

# Configure logging system
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
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
_permission_buffer: list = []
_permission_buffer_max = 20

# WebSocket connection rate limiter: client_ip -> list of recent connection timestamps
_ws_conn_attempts: Dict[str, list] = defaultdict(list)
_ws_rate_window = 60  # seconds

def _check_ws_rate_limit(client_ip: str) -> bool:
    """Return True if connection is allowed, False if rate limited."""
    now = time.time()
    window_start = now - _ws_rate_window
    _ws_conn_attempts[client_ip] = [
        ts for ts in _ws_conn_attempts[client_ip] if ts > window_start
    ]
    max_ws = int(settings.RATE_LIMIT_WEBSOCKET.split("/")[0]) if hasattr(settings, 'RATE_LIMIT_WEBSOCKET') else 5
    if len(_ws_conn_attempts[client_ip]) >= max_ws:
        return False
    _ws_conn_attempts[client_ip].append(now)
    return True

async def _buffer_events(event: SystemEvent):
    exec_id = event.payload.get("execution_id")
    if exec_id:
        _event_buffer[exec_id].append(event.model_dump())
        if len(_event_buffer[exec_id]) > _event_buffer_max:
            _event_buffer[exec_id] = _event_buffer[exec_id][-_event_buffer_max:]

    if event.topic == "permission.request":
        _permission_buffer.append(event.model_dump())
        if len(_permission_buffer) > _permission_buffer_max:
            _permission_buffer.pop(0)

async def _resolve_ws_user(websocket: WebSocket):
    """Extract and validate JWT from WebSocket query params. Returns User or raises."""
    from app.infrastructure.db.models import User
    token = websocket.query_params.get("token")
    if not token:
        await websocket.accept()
        await websocket.close(code=4001, reason="Authentication required")
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if not email:
            await websocket.accept()
            await websocket.close(code=4001, reason="Invalid token")
            return None
        user = await User.find_one(User.email == email)
        if not user:
            await websocket.accept()
            await websocket.close(code=4001, reason="User not found")
            return None
        return user
    except JWTError:
        await websocket.accept()
        await websocket.close(code=4001, reason="Invalid or expired token")
        return None

async def _check_ws_ownership(execution_id: str, user_id: str) -> bool:
    """Verify the execution belongs to the given user."""
    from app.services.workflow_engine import _find_exec
    exec_doc = await _find_exec(execution_id)
    if not exec_doc:
        return False
    return str(exec_doc.get("user_id", "")) == str(user_id)

async def _check_permission_ownership(event: SystemEvent, user_id: str) -> bool:
    """Check if a permission.request event relates to an execution owned by user_id."""
    exec_id = event.payload.get("execution_id")
    if not exec_id:
        return True
    return await _check_ws_ownership(exec_id, user_id)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup diagnostics (non-sensitive only) ---
    logger.info("=" * 60)
    logger.info("ACO FastAPI Starting Up")
    logger.info("=" * 60)
    logger.info(f"  Environment:   development")
    logger.info(f"  Ollama URL:    {settings.OLLAMA_BASE_URL}")
    logger.info(f"  Ollama model:  {settings.OLLAMA_MODEL}")
    logger.info(f"  MongoDB URL:   {settings.MONGODB_URL.split('@')[-1] if '@' in settings.MONGODB_URL else settings.MONGODB_URL}")
    logger.info(f"  Redis enabled: {settings.REDIS_ENABLED}")
    logger.info(f"  CORS origins:  {settings.cors_origins_list}")
    logger.info(f"  Frontend URL:  http://localhost:3000")
    logger.info("=" * 60)

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
    for topic in ["task.started", "task.progress", "task.completed", "task.failed",
                   "verification.failed", "workflow.state_change", "permission.request",
                   "workflow.cancelled"]:
        event_bus.subscribe(topic, _buffer_events)

    # 3. Start background Worker Pool (3 concurrency workers)
    await worker_pool.start(num_workers=3)

    # 4. Start background directory file indexing crawl loop
    file_indexer.start()

    logger.info("ACO FastAPI startup complete.")
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
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Mount API routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    db_health = db_manager.health_dict()
    overall = "healthy" if db_manager.connected else "degraded"
    return {
        "status": overall,
        "project": settings.PROJECT_NAME,
        "database": db_health["mongodb"],
        "redis": db_health["redis"],
    }


@app.websocket("/ws/executions/{execution_id}")
async def ws_execution_monitor(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint enabling live updates (screen, step progress, permissions)
    to stream directly to the Electron UI dashboard client.
    Requires a valid JWT token. Only streams events belonging to the authenticated user.
    """
    # WebSocket connection rate limit (per client IP)
    client_ip = websocket.client.host if websocket.client else "unknown"
    if not _check_ws_rate_limit(client_ip):
        await websocket.accept()
        await websocket.close(code=4008, reason="Too many connections, try again later")
        return

    # Require valid JWT token — reject unauthenticated connections
    user = await _resolve_ws_user(websocket)
    if user is None:
        return

    # Verify the execution belongs to this user
    if not await _check_ws_ownership(execution_id, str(user.id)):
        await websocket.accept()
        await websocket.close(code=4003, reason="Execution not found or access denied")
        return

    await websocket.accept()
    logger.info(f"WebSocket client connected: user={user.email}, execution={execution_id}")

    # Replay any buffered events that fired before the WebSocket connected
    buffered = _event_buffer.pop(execution_id, [])
    replayed = 0
    for event_data in buffered:
        event_exec_id = event_data.get("payload", {}).get("execution_id", "")
        if event_exec_id == execution_id:
            try:
                await websocket.send_json(event_data)
                replayed += 1
            except Exception:
                pass
    if replayed > 0:
        logger.info(f"Replayed {replayed} buffered events for execution {execution_id}")

    # Channel event forwarding queue
    event_queue = asyncio.Queue()

    async def event_forwarder(event: SystemEvent):
        payload_exec_id = event.payload.get("execution_id")
        is_permission = event.topic == "permission.request"

        if is_permission or payload_exec_id == execution_id:
            if not is_permission:
                # Verify ownership for execution events
                if not await _check_ws_ownership(execution_id, str(user.id)):
                    return
            else:
                # Verify ownership for permission events
                if not await _check_permission_ownership(event, str(user.id)):
                    return
            try:
                await event_queue.put(event.model_dump())
            except Exception:
                pass

    forwarder_topics = [
        "workflow.state_change", "task.progress", "task.started",
        "task.completed", "task.failed", "permission.request", "verification.failed",
        "workflow.cancelled",
    ]
    for topic in forwarder_topics:
        event_bus.subscribe(topic, event_forwarder)

    # Replay pending permission events (only those owned by this user)
    if _permission_buffer:
        pending_perms = list(_permission_buffer)
        _permission_buffer.clear()
        for perm_event in pending_perms:
            if await _check_permission_ownership(
                SystemEvent(**perm_event) if isinstance(perm_event, dict) else perm_event,
                str(user.id)
            ):
                try:
                    await websocket.send_json(perm_event)
                    logger.info(f"Replayed buffered permission event {perm_event.get('payload', {}).get('request_id', '?')} to WebSocket")
                except Exception:
                    pass

    try:
        while True:
            try:
                event_data = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                await websocket.send_json(event_data)
            except asyncio.TimeoutError:
                pass

            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: user={user.email}, execution={execution_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket execution stream: {e}")
    finally:
        for topic in forwarder_topics:
            event_bus.unsubscribe(topic, event_forwarder)
        logger.info(f"Cleaned up {len(forwarder_topics)} event subscriptions for execution: {execution_id}")
