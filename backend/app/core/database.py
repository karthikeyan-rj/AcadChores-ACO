import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from redis.asyncio import Redis, from_url
from app.core.config import settings
from app.infrastructure.db.models import (
    User, Workflow, WorkflowExecution, TaskLog, PermissionPolicy, FileIndex, MemoryStore,
    IndexConfig, IndexJob, UserApiKey, FallbackUsage, UserSettings
)

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.mongo_client: AsyncIOMotorClient = None
        self.redis_client: Redis = None
        self.use_memory: bool = True  # True only if MongoDB is unavailable
        self.db = None

    async def initialize(self):
        logger.info("Initializing database connections...")

        # 1. Connect to MongoDB
        try:
            self.mongo_client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=5000)
            self.mongo_client.append_metadata = lambda *args, **kwargs: None
            try:
                self.db = self.mongo_client.get_default_database()
            except Exception:
                self.db = self.mongo_client[settings.MONGODB_DATABASE]
            await asyncio.wait_for(
                init_beanie(
                    database=self.db,
                    document_models=[User, Workflow, WorkflowExecution, TaskLog, PermissionPolicy, FileIndex, MemoryStore, IndexConfig, IndexJob, UserApiKey, FallbackUsage, UserSettings]
                ),
                timeout=10.0
            )
            await asyncio.wait_for(self.db.command("ping"), timeout=5.0)
            self.use_memory = False
            logger.info("Successfully connected to MongoDB — using real database.")
        except Exception as e:
            self.use_memory = True
            logger.warning(f"MongoDB offline: {e}. Using In-Memory storage.")

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

    async def close(self):
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass

db_manager = DatabaseManager()
