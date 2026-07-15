import logging
import asyncio
import re
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from redis.asyncio import Redis, from_url
from app.core.config import settings
from app.infrastructure.db.models import (
    User, Workflow, WorkflowExecution, TaskLog, PermissionPolicy, FileIndex, MemoryStore,
    IndexConfig, IndexJob, UserApiKey, FallbackUsage, UserSettings
)

logger = logging.getLogger(__name__)

def _sanitize_mongo_url(url: str) -> str:
    """Strip credentials from MongoDB URL for safe logging. Never include in error messages."""
    if "@" in url:
        return url.split("@")[-1]
    return "localhost"


def _classify_connection_error(exc: Exception) -> str:
    """Classify a MongoDB connection error into a human-readable, sanitized reason."""
    msg = str(exc).lower()
    if "dns" in msg or "srv" in msg or "name or service not known" in msg:
        return "DNS/SRV resolution failed — check cluster hostname"
    if "authentication" in msg or "auth" in msg or "authentication fail" in msg:
        return "Authentication failed — check username and password"
    if "tls" in msg or "ssl" in msg or "certificate" in msg:
        return "TLS/SSL error — do not disable certificate verification"
    if "timeout" in msg or "timed out" in msg:
        return "Connection timeout — check network access and IP allowlist"
    if "connection refused" in msg or "connectionreset" in msg:
        return "Connection refused — check IP is in Atlas Network Access allowlist"
    if "invalid" in msg and ("uri" in msg or "connection string" in msg):
        return "Malformed connection string — check URI format"
    return f"Connection failed: {type(exc).__name__}"


class DatabaseManager:
    def __init__(self):
        self.mongo_client: AsyncIOMotorClient = None
        self.redis_client: Redis = None
        self.use_memory: bool = True  # True only if MongoDB is unavailable
        self.db = None
        self.connected: bool = False
        self.connection_method: str = "memory"

    async def initialize(self):
        logger.info("Initializing database connections...")

        # 1. Connect to MongoDB
        is_atlas = "mongodb+srv" in settings.MONGODB_URL
        try:
            self.mongo_client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                tlsAllowInvalidCertificates=False,
            )
            # Motor compat shim for memory_db integration
            self.mongo_client.append_metadata = lambda *args, **kwargs: None

            # Resolve database: prefer URL-embedded name, fall back to config
            try:
                self.db = self.mongo_client.get_default_database()
            except Exception:
                self.db = self.mongo_client[settings.MONGODB_DATABASE]

            # Initialize BeanieODM with all document models
            await asyncio.wait_for(
                init_beanie(
                    database=self.db,
                    document_models=[
                        User, Workflow, WorkflowExecution, TaskLog,
                        PermissionPolicy, FileIndex, MemoryStore, IndexConfig,
                        IndexJob, UserApiKey, FallbackUsage, UserSettings,
                    ]
                ),
                timeout=10.0,
            )

            # Verify connection with explicit ping
            await asyncio.wait_for(self.db.command("ping"), timeout=5.0)

            self.use_memory = False
            self.connected = True
            self.connection_method = "atlas" if is_atlas else "local"
            host = _sanitize_mongo_url(settings.MONGODB_URL)
            logger.info(f"Connected to MongoDB ({self.connection_method}) — host: {host}, database: {self.db.name}")

        except Exception as e:
            self.use_memory = True
            self.connected = False
            self.connection_method = "memory"
            reason = _classify_connection_error(e)
            logger.warning(f"MongoDB unavailable: {reason}. Using in-memory storage.")
            logger.debug(f"Raw MongoDB error (sanitized): {type(e).__name__}")

        # 2. Connect to Redis (for event bus / task queue)
        if not settings.REDIS_ENABLED:
            self.redis_client = None
            logger.info("Redis disabled by configuration (REDIS_ENABLED=false). Using in-memory event bus and task queue.")
        else:
            try:
                self.redis_client = from_url(settings.REDIS_URL, decode_responses=True)
                await asyncio.wait_for(self.redis_client.ping(), timeout=3.0)
                logger.info("Successfully connected to Redis.")
            except Exception as e:
                self.redis_client = None
                logger.warning(f"Redis offline: {e}. Using in-memory event bus and task queue.")

    def health_dict(self) -> dict:
        """Return sanitized health status for the /health endpoint. No secrets."""
        return {
            "mongodb": {
                "status": "connected" if self.connected else "disconnected",
                "method": self.connection_method,
                "database": self.db.name if self.db is not None else None,
            },
            "redis": {
                "status": "connected" if self.redis_client else ("disabled" if not settings.REDIS_ENABLED else "disconnected"),
            },
        }

    async def close(self):
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass

db_manager = DatabaseManager()
