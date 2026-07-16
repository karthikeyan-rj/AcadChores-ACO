import logging
import asyncio
import re
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from redis.asyncio import Redis, from_url
from app.core.config import settings
from app.infrastructure.db.models import (
    User, Workflow, WorkflowExecution, TaskLog, PermissionPolicy, FileIndex, MemoryStore,
    IndexConfig, IndexJob, UserApiKey, FallbackUsage, UserSettings, ChatMessage, Conversation
)

logger = logging.getLogger(__name__)

# Beanie document models registered at startup
_BEANIE_MODELS = [
    User, Workflow, WorkflowExecution, TaskLog,
    PermissionPolicy, FileIndex, MemoryStore, IndexConfig,
    IndexJob, UserApiKey, FallbackUsage, UserSettings, ChatMessage, Conversation,
]


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
        self._beanie_model_count: int = 0

    async def initialize(self):
        logger.info("Initializing database connections...")

        is_atlas = "mongodb+srv" in settings.MONGODB_URL
        fallback_allowed = settings.ALLOW_DATABASE_FALLBACK

        # 1. Connect to MongoDB
        try:
            self.mongo_client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
                tlsAllowInvalidCertificates=False,
            )
            # Motor compat shim for memory_db integration
            self.mongo_client.append_metadata = lambda *args, **kwargs: None

            # Resolve database: always use configured database name for consistency
            self.db = self.mongo_client[settings.MONGODB_DATABASE]

            # Initialize BeanieODM with all document models
            await asyncio.wait_for(
                init_beanie(
                    database=self.db,
                    document_models=_BEANIE_MODELS,
                ),
                timeout=10.0,
            )
            self._beanie_model_count = len(_BEANIE_MODELS)

            # Safe unique email index migration
            await self._migrate_unique_email_index()

            # Verify connection with explicit ping
            await asyncio.wait_for(self.db.command("ping"), timeout=5.0)

            self.use_memory = False
            self.connected = True
            self.connection_method = "atlas" if is_atlas else "local"

            # Structured startup diagnostics (no credentials)
            logger.info("=" * 50)
            logger.info("MongoDB mode: %s", self.connection_method.upper())
            logger.info("Database: %s", self.db.name)
            logger.info("MongoDB ping: successful")
            logger.info("Beanie initialization: successful")
            logger.info("Registered models: %d", self._beanie_model_count)
            logger.info("Fallback mode: %s", "enabled" if fallback_allowed else "disabled")
            logger.info("=" * 50)

        except Exception as e:
            reason = _classify_connection_error(e)

            if is_atlas and not fallback_allowed:
                # Atlas is required but unavailable — fail startup
                logger.error("=" * 50)
                logger.error("FATAL: MongoDB Atlas is required but unavailable.")
                logger.error("Reason: %s", reason)
                logger.error("Set ALLOW_DATABASE_FALLBACK=true in .env to allow")
                logger.error("in-memory fallback (data will NOT persist across restarts).")
                logger.error("=" * 50)
                raise RuntimeError(
                    f"MongoDB Atlas is required but unavailable: {reason}. "
                    f"Set ALLOW_DATABASE_FALLBACK=true to allow in-memory fallback."
                ) from e

            # Fallback allowed — continue with in-memory storage
            self.use_memory = True
            self.connected = False
            self.connection_method = "memory"
            logger.warning("MongoDB unavailable: %s. Using in-memory storage.", reason)
            logger.warning("Data will NOT persist across backend restarts.")
            logger.info("=" * 50)
            logger.info("MongoDB mode: MEMORY")
            logger.info("Database: N/A")
            logger.info("MongoDB ping: N/A")
            logger.info("Beanie initialization: N/A")
            logger.info("Registered models: 0")
            logger.info("Fallback mode: enabled")
            logger.info("=" * 50)

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
                "mode": self.connection_method,
                "database": self.db.name if self.db is not None else None,
                "fallback": self.use_memory,
            },
            "redis": {
                "status": "connected" if self.redis_client else ("disabled" if not settings.REDIS_ENABLED else "disconnected"),
            },
        }

    async def _migrate_unique_email_index(self):
        """Safely migrate to unique email index. Detects duplicates, normalizes, and deduplicates."""
        if self.use_memory or self.db is None:
            return

        try:
            import pymongo
            collection = self.db["users"]

            # Find duplicate emails (case-insensitive)
            pipeline = [
                {"$group": {"_id": {"$toLower": "$email"}, "count": {"$sum": 1}, "ids": {"$push": "$_id"}}},
                {"$match": {"count": {"$gt": 1}}},
            ]
            duplicates = await collection.aggregate(pipeline).to_list(length=100)

            if duplicates:
                logger.warning("Found %d duplicate email groups — normalizing and deduplicating...", len(duplicates))
                for group in duplicates:
                    canonical_email = group["_id"]
                    ids = group["ids"]
                    # Keep the first document (oldest), remove the rest
                    keep_id = ids[0]
                    remove_ids = ids[1:]
                    # Merge any unique data from duplicates into the canonical one
                    for rid in remove_ids:
                        dup_doc = await collection.find_one({"_id": rid})
                        if dup_doc:
                            # Update canonical with any non-null fields from duplicate
                            update_fields = {}
                            for field in ["google_id", "avatar_url", "last_login_at"]:
                                if dup_doc.get(field) and not (await collection.find_one({"_id": keep_id})).get(field):
                                    update_fields[field] = dup_doc[field]
                            if update_fields:
                                await collection.update_one({"_id": keep_id}, {"$set": update_fields})
                            # Remove duplicate
                            await collection.delete_one({"_id": rid})
                            logger.info("  Deduplicated: removed %s, kept %s for email '%s'", rid, keep_id, canonical_email)

                # Normalize all emails to lowercase
                await collection.update_many(
                    {"email": {"$ne": {"$toLower": "$email"}}},
                    [{"$set": {"email": {"$toLower": "$email"}}}],
                )
                logger.info("All user emails normalized to lowercase.")

            # Ensure unique index exists (idempotent)
            existing_indexes = await collection.index_information()
            email_index_name = None
            for name, info in existing_indexes.items():
                if any(k == "email" for k, v in info.get("key", []) if isinstance(v, str) or (isinstance(info.get("key"), list) and any(pair[0] == "email" for pair in info["key"]))):
                    # Check if this index has email as a key
                    key_pairs = info.get("key", [])
                    if any(pair[0] == "email" for pair in key_pairs):
                        email_index_name = name
                        break

            if email_index_name and not existing_indexes.get(email_index_name, {}).get("unique"):
                # Drop old non-unique email index, create unique one
                logger.info("Migrating email index to unique (dropping '%s')...", email_index_name)
                await collection.drop_index(email_index_name)

            # Create unique email index (idempotent if already exists)
            await collection.create_index("email", unique=True, name="email_unique_idx")
            logger.info("Unique email index ensured.")

        except Exception as e:
            logger.warning("Email index migration skipped (non-fatal): %s", type(e).__name__)

    async def close(self):
        if self.mongo_client:
            self.mongo_client.close()
        if self.redis_client:
            try:
                await self.redis_client.aclose()
            except Exception:
                pass

db_manager = DatabaseManager()
