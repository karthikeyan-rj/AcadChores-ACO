"""
Shared test fixtures for ACO backend tests.

CRITICAL: Environment variables are set BEFORE any app imports to ensure
the test database override takes effect before the Settings singleton is created.
Additionally, the settings singleton is patched directly since .env takes
precedence over os.environ in pydantic-settings.
"""
import os

# Set test database BEFORE any app imports
os.environ["MONGODB_DATABASE"] = "aco_test"
os.environ["ALLOW_DATABASE_FALLBACK"] = "false"
os.environ["APP_ENV"] = "test"

import pytest
from app.core.config import settings, normalize_email
from app.core.database import db_manager
from app.infrastructure.memory_db import _in_memory_collections, PERSIST_FILE

# SAFETY: Patch the settings singleton to use test database
# This is needed because .env file takes precedence over os.environ in pydantic-settings
settings.MONGODB_DATABASE = "aco_test"
# Allow fallback for tests — when Atlas is unreachable, tests run in memory mode
settings.ALLOW_DATABASE_FALLBACK = True

# Confirm test database is active
assert settings.MONGODB_DATABASE == "aco_test", (
    f"Test database override failed! Got '{settings.MONGODB_DATABASE}', expected 'aco_test'. "
    "conftest.py env vars must be set before any app imports."
)
# Confirm fallback is allowed for tests
assert settings.ALLOW_DATABASE_FALLBACK is True, (
    "ALLOW_DATABASE_FALLBACK must be True for tests to handle Atlas unavailability."
)

# SAFETY: Never run tests against the production database
if settings.MONGODB_URL.startswith("mongodb+srv") and settings.MONGODB_DATABASE == "aco":
    raise RuntimeError(
        "Tests must NOT run against the production 'aco' database. "
        "Set MONGODB_DATABASE=aco_test in environment or conftest.py."
    )


def _purge_test_data():
    """Delete ONLY test data from the test database. Never touches production."""
    db_name = settings.MONGODB_DATABASE
    if db_name != "aco_test":
        raise RuntimeError(f"Refusing to purge non-test database '{db_name}'. Expected 'aco_test'.")

    if db_manager.use_memory:
        for coll in _in_memory_collections.values():
            coll.clear()
        return

    try:
        import pymongo
        sync_client = pymongo.MongoClient(
            settings.MONGODB_URL, serverSelectionTimeoutMS=5000,
            tlsAllowInvalidCertificates=False,
        )
        try:
            sync_db = sync_client[db_name]
            # Delete all test users and test data from aco_test
            sync_db.users.delete_many({})
            sync_db.chat_messages.delete_many({})
            sync_db.workflows.delete_many({})
            sync_db.workflow_executions.delete_many({})
            sync_db.user_settings.delete_many({})
            sync_db.conversations.delete_many({})
            sync_db.user_api_keys.delete_many({})
            sync_db.task_logs.delete_many({})
        finally:
            sync_client.close()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Test data purge failed: %s", type(e).__name__)


@pytest.fixture(autouse=True)
def _reset_test_state():
    """Reset rate limiter, memory DB, and test data before each test."""
    from app.core.rate_limit import limiter

    # Reset slowapi rate limiter storage
    storage = limiter._storage
    if hasattr(storage, "reset"):
        storage.reset()
    elif hasattr(storage, "storage") and hasattr(storage.storage, "clear"):
        storage.storage.clear()

    # Clear in-memory collections
    for coll in _in_memory_collections.values():
        coll.clear()

    # Remove persisted data file if it exists
    if os.path.exists(PERSIST_FILE):
        try:
            os.remove(PERSIST_FILE)
        except OSError:
            pass

    # Purge test data from MongoDB test database
    _purge_test_data()

    yield

    # Cleanup after test
    for coll in _in_memory_collections.values():
        coll.clear()
    _purge_test_data()
    if hasattr(storage, "reset"):
        storage.reset()
    elif hasattr(storage, "storage") and hasattr(storage.storage, "clear"):
        storage.storage.clear()


@pytest.fixture(scope="session")
def client():
    from starlette.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(autouse=True)
def _patch_file_agent_workspace(request):
    """Allow FileAgent to operate on any path during tests (bypasses workspace validation).
    Skip for tests marked with @pytest.mark.real_workspace."""
    if request.node.get_closest_marker("real_workspace"):
        yield
        return
    from unittest.mock import patch
    with patch("app.services.agent_dispatcher.FileAgent._validate_workspace", return_value=None):
        yield
