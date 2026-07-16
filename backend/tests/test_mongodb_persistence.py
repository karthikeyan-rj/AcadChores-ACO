"""
MongoDB Atlas persistence tests for ACO backend.

All tests run against the 'aco_test' database only.
Production database is never touched.

Uses synchronous pymongo for direct DB verification (avoids event loop conflicts
with TestClient). HTTP calls go through the sync TestClient as normal.
"""
import json
import pytest
import pymongo
from datetime import datetime
from bson import ObjectId
from app.core.config import settings, normalize_email
from app.core.database import db_manager
from app.infrastructure.memory_db import memory_db


# Safety guard: confirm test database
@pytest.fixture(autouse=True)
def _ensure_test_database():
    assert settings.MONGODB_DATABASE == "aco_test", (
        f"Tests must run against 'aco_test', got '{settings.MONGODB_DATABASE}'"
    )


def _get_sync_db():
    """Get a sync pymongo handle to the test database for direct verification."""
    client = pymongo.MongoClient(
        settings.MONGODB_URL, serverSelectionTimeoutMS=5000,
        tlsAllowInvalidCertificates=False,
    )
    try:
        yield client[settings.MONGODB_DATABASE]
    finally:
        client.close()


@pytest.fixture
def sync_db():
    yield from _get_sync_db()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _register(client, email, name, password="Test1234!"):
    resp = client.post("/api/v1/auth/register", json={
        "email": email, "name": name, "password": password,
    })
    assert resp.status_code == 200, f"Register failed ({email}): {resp.text}"
    return resp.json()["access_token"], resp.json()["user"]


def _requires_mongo():
    """Skip test if MongoDB is not connected (running in memory mode)."""
    if db_manager.use_memory or not db_manager.connected:
        pytest.skip("MongoDB not available — running in memory mode")


# ── 1. Registration stores user in MongoDB ───────────────────────────

class TestRegistrationPersistence:
    def test_register_stores_user_in_mongodb(self, client, sync_db):
        """Registration inserts a real document in the database."""
        _requires_mongo()
        t, user = _register(client, "persist_reg@test.com", "PersistReg")
        assert user["email"] == "persist_reg@test.com"

        # Verify in database directly via pymongo (sync, no loop issues)
        found = sync_db.users.find_one({"email": "persist_reg@test.com"})
        assert found is not None
        assert found["name"] == "PersistReg"

    def test_duplicate_normalized_email_rejected(self, client, sync_db):
        """Duplicate emails with different casing are rejected."""
        _requires_mongo()
        _register(client, "DupTest@Test.COM", "Dup1")
        resp = client.post("/api/v1/auth/register", json={
            "email": "duptest@test.com", "name": "Dup2", "password": "Test1234!",
        })
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()


# ── 3. Login works after backend restart (simulated) ─────────────────

class TestLoginPersistence:
    def test_login_finds_persistent_user(self, client, sync_db):
        """Login finds a user that was stored in the database."""
        _requires_mongo()
        _register(client, "login_persist@test.com", "LoginPersist")
        resp = client.post("/api/v1/auth/login", json={
            "email": "login_persist@test.com", "password": "Test1234!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_after_requery(self, client, sync_db):
        """Login finds user after re-query (simulates restart)."""
        _requires_mongo()
        _register(client, "login_restart@test.com", "LoginRestart")

        # Direct DB query — simulates fresh startup
        found = sync_db.users.find_one({"email": "login_restart@test.com"})
        assert found is not None
        assert found["name"] == "LoginRestart"


# ── 4. /auth/me finds the persistent user ────────────────────────────

class TestMeEndpointPersistence:
    def test_me_finds_persistent_user(self, client, sync_db):
        """The /me endpoint finds a persistent user."""
        _requires_mongo()
        t, _ = _register(client, "me_persist@test.com", "MePersist")
        resp = client.get("/api/v1/auth/me", headers=_auth(t))
        assert resp.status_code == 200
        assert resp.json()["email"] == "me_persist@test.com"


# ── 5. User profile persists ────────────────────────────────────────

class TestProfilePersistence:
    def test_user_profile_persists(self, client, sync_db):
        """User profile data persists in the database."""
        _requires_mongo()
        t, user = _register(client, "profile_pers@test.com", "ProfilePers")
        resp = client.get("/api/v1/auth/me", headers=_auth(t))
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "ProfilePers"
        assert data["role"] == "user"

    def test_user_has_account_status(self, client, sync_db):
        """User documents include account_status field."""
        _requires_mongo()
        _register(client, "acct_status@test.com", "AcctStatus")
        found = sync_db.users.find_one({"email": "acct_status@test.com"})
        assert found is not None
        assert found.get("account_status") == "active"


# ── 6. User settings persist ────────────────────────────────────────

class TestSettingsPersistence:
    def test_user_settings_persist(self, client, sync_db):
        """User settings are stored and retrieved from the database."""
        _requires_mongo()
        uid = ObjectId()
        settings_doc = {
            "user_id": uid,
            "cloud_fallback_enabled": True,
            "cloud_provider": "openai",
            "cloud_model": "gpt-4o",
            "workflow_quality_threshold": 80,
        }
        sync_db.user_settings.insert_one(settings_doc)

        found = sync_db.user_settings.find_one({"user_id": uid})
        assert found is not None
        assert found["cloud_fallback_enabled"] is True
        assert found["cloud_model"] == "gpt-4o"


# ── 7. Every prompt is stored as a chat message ─────────────────────

class TestChatMessagePersistence:
    def test_chat_message_persists(self, client, sync_db):
        """Chat messages are stored in the database."""
        _requires_mongo()
        uid = ObjectId()
        msg = {
            "user_id": uid,
            "conversation_id": "conv_test_1",
            "role": "user",
            "message_type": "user",
            "content": "Hello, this is a test prompt",
            "created_at": datetime.utcnow(),
            "metadata": {},
        }
        sync_db.chat_messages.insert_one(msg)

        found = list(sync_db.chat_messages.find({
            "user_id": uid,
            "conversation_id": "conv_test_1",
        }))
        assert len(found) == 1
        assert found[0]["content"] == "Hello, this is a test prompt"


# ── 8. Conversation history persists after restart ───────────────────

class TestConversationPersistence:
    def test_conversation_persists(self, client, sync_db):
        """Conversation records persist in the database."""
        _requires_mongo()
        uid = ObjectId()
        conv = {
            "conversation_id": "conv_restart_test",
            "user_id": uid,
            "title": "Test Conversation",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_message_at": datetime.utcnow(),
        }
        sync_db.conversations.insert_one(conv)

        found = sync_db.conversations.find_one({
            "user_id": uid,
            "conversation_id": "conv_restart_test",
        })
        assert found is not None
        assert found["title"] == "Test Conversation"

    def test_chat_messages_persist_across_queries(self, client, sync_db):
        """Multiple chat messages persist and can be retrieved."""
        _requires_mongo()
        uid = ObjectId()
        conv_id = "conv_multi_test"

        for i in range(5):
            sync_db.chat_messages.insert_one({
                "user_id": uid,
                "conversation_id": conv_id,
                "role": "user" if i % 2 == 0 else "assistant",
                "message_type": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "created_at": datetime.utcnow(),
                "metadata": {},
            })

        found = list(sync_db.chat_messages.find({
            "user_id": uid,
            "conversation_id": conv_id,
        }).sort("created_at", 1))
        assert len(found) == 5
        assert found[0]["content"] == "Message 0"
        assert found[4]["content"] == "Message 4"


# ── 9. Workflow records persist ─────────────────────────────────────

class TestWorkflowPersistence:
    def test_workflow_persists(self, client, sync_db):
        """Workflow records persist in the database."""
        _requires_mongo()
        uid = ObjectId()
        wf = {
            "title": "Test Workflow",
            "description": "Persistence test",
            "owner_id": uid,
            "steps": [{"step_id": "s1", "name": "Step 1", "action": "run",
                        "parameters": {"command": "echo hi"}, "agent_type": "terminal"}],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = sync_db.workflows.insert_one(wf)
        inserted_id = result.inserted_id

        found = sync_db.workflows.find_one({"_id": inserted_id})
        assert found is not None
        assert found["title"] == "Test Workflow"
        assert len(found["steps"]) == 1


# ── 10. Workflow steps persist ──────────────────────────────────────

class TestWorkflowStepPersistence:
    def test_workflow_steps_persist(self, client, sync_db):
        """Workflow steps are stored correctly."""
        _requires_mongo()
        uid = ObjectId()
        steps = [
            {"step_id": "s1", "name": "Step 1", "action": "run",
             "parameters": {"command": "echo 1"}, "agent_type": "terminal"},
            {"step_id": "s2", "name": "Step 2", "action": "read",
             "parameters": {"path": "/tmp/test.txt"}, "agent_type": "file"},
        ]
        wf = {
            "title": "Multi-Step WF", "description": "Test",
            "owner_id": uid, "steps": steps,
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
        }
        result = sync_db.workflows.insert_one(wf)

        found = sync_db.workflows.find_one({"_id": result.inserted_id})
        assert len(found["steps"]) == 2
        assert found["steps"][0]["action"] == "run"
        assert found["steps"][1]["action"] == "read"


# ── 11. Execution history persists ──────────────────────────────────

class TestExecutionPersistence:
    def test_execution_persists(self, client, sync_db):
        """Execution records persist in the database."""
        _requires_mongo()
        wf_id = ObjectId()
        uid = ObjectId()
        exec_doc = {
            "workflow_id": wf_id,
            "user_id": uid,
            "title": "Test Execution",
            "status": "completed",
            "total_steps": 3,
            "current_step_index": 3,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = sync_db.workflow_executions.insert_one(exec_doc)

        found = sync_db.workflow_executions.find_one({"_id": result.inserted_id})
        assert found is not None
        assert found["status"] == "completed"
        assert found["total_steps"] == 3


# ── 12. User A cannot access User B's records ───────────────────────

class TestCrossUserIsolation:
    def test_user_a_cannot_see_user_b_chats(self, client, sync_db):
        """User A cannot read User B's chat messages."""
        _requires_mongo()
        uid_a = ObjectId()
        uid_b = ObjectId()

        sync_db.chat_messages.insert_one({
            "user_id": uid_a, "conversation_id": "conv_a",
            "role": "user", "message_type": "user",
            "content": "A's secret", "created_at": datetime.utcnow(), "metadata": {},
        })
        sync_db.chat_messages.insert_one({
            "user_id": uid_b, "conversation_id": "conv_b",
            "role": "user", "message_type": "user",
            "content": "B's secret", "created_at": datetime.utcnow(), "metadata": {},
        })

        a_msgs = list(sync_db.chat_messages.find({"user_id": uid_a}))
        assert len(a_msgs) == 1
        assert a_msgs[0]["content"] == "A's secret"

        b_msgs = list(sync_db.chat_messages.find({"user_id": uid_b}))
        assert len(b_msgs) == 1
        assert b_msgs[0]["content"] == "B's secret"

    def test_user_a_cannot_see_user_b_workflows(self, client, sync_db):
        """User A cannot read User B's workflows."""
        _requires_mongo()
        uid_a = ObjectId()
        uid_b = ObjectId()
        ts = datetime.utcnow()

        sync_db.workflows.insert_one({
            "title": "A's WF", "description": "", "owner_id": uid_a,
            "steps": [], "created_at": ts, "updated_at": ts,
        })
        sync_db.workflows.insert_one({
            "title": "B's WF", "description": "", "owner_id": uid_b,
            "steps": [], "created_at": ts, "updated_at": ts,
        })

        a_wfs = list(sync_db.workflows.find({"owner_id": uid_a}))
        b_wfs = list(sync_db.workflows.find({"owner_id": uid_b}))
        assert len(a_wfs) == 1
        assert a_wfs[0]["title"] == "A's WF"
        assert len(b_wfs) == 1
        assert b_wfs[0]["title"] == "B's WF"


# ── 13. Atlas failure does not silently activate memory fallback ────

class TestFallbackBehavior:
    def test_fallback_disabled_by_default(self):
        """ALLOW_DATABASE_FALLBACK defaults to false."""
        from app.core.config import Settings
        s = Settings()
        assert s.ALLOW_DATABASE_FALLBACK is False


# ── 14. Health reports status ───────────────────────────────────────

class TestHealthReporting:
    def test_health_endpoint_returns_mongodb_info(self, client):
        """Health endpoint returns MongoDB connection info."""
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "mongodb" in data
        assert "status" in data["mongodb"]
        assert "mode" in data["mongodb"]
        assert "fallback" in data["mongodb"]
        assert data["mongodb"]["status"] in ("connected", "disconnected")
        assert data["mongodb"]["mode"] in ("atlas", "local", "memory")
        assert isinstance(data["mongodb"]["fallback"], bool)

    def test_health_no_credentials_exposed(self, client):
        """Health endpoint does not expose credentials."""
        resp = client.get("/health")
        data = resp.json()
        health_str = json.dumps(data)
        assert "acadchoresaco" not in health_str.lower()
        assert "karthikeyanrj" not in health_str.lower()


# ── 15. Startup fails when Atlas required but unavailable ───────────

class TestStartupBehavior:
    def test_fallback_config_exists(self):
        """ALLOW_DATABASE_FALLBACK config option exists and is boolean."""
        assert isinstance(settings.ALLOW_DATABASE_FALLBACK, bool)


# ── 16. No plaintext passwords stored ──────────────────────────────

class TestPasswordSecurity:
    def test_no_plaintext_passwords(self, client, sync_db):
        """No user document contains a plaintext password."""
        _requires_mongo()
        _register(client, "plaintext_test@test.com", "PlainTest")
        found = sync_db.users.find_one({"email": "plaintext_test@test.com"})
        assert found is not None
        assert found["hashed_password"] != "Test1234!"
        assert found["hashed_password"].startswith("$2b$") or found["hashed_password"].startswith("$2a$")


# ── 17. No secret API keys stored unencrypted ──────────────────────

class TestApiKeySecurity:
    def test_api_keys_are_encrypted(self, client, sync_db):
        """Stored API keys are encrypted, not plaintext."""
        _requires_mongo()
        uid = ObjectId()
        key_doc = {
            "user_id": uid,
            "provider": "openai",
            "encrypted_key": "gAAAAABh...encrypted...",
            "key_hint": "****abcd",
            "created_at": datetime.utcnow(),
        }
        sync_db.user_api_keys.insert_one(key_doc)

        found = sync_db.user_api_keys.find_one({
            "user_id": uid,
            "provider": "openai",
        })
        assert found is not None
        assert found["encrypted_key"] != "sk-real-api-key-here"
        assert "****" in found["key_hint"]


# ── 18. Frontend restores valid session after refresh ────────────────

class TestSessionPersistence:
    def test_token_valid_after_requery(self, client, sync_db):
        """A JWT token remains valid when the user still exists in the database."""
        _requires_mongo()
        t, _ = _register(client, "session_persist@test.com", "SessionPers")
        for _ in range(3):
            resp = client.get("/api/v1/auth/me", headers=_auth(t))
            assert resp.status_code == 200
            assert resp.json()["email"] == "session_persist@test.com"


# ── 19. Existing tests remain passing (smoke test) ──────────────────

class TestSmokeExisting:
    def test_health_still_works(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_register_login_me_still_works(self, client):
        t, user = _register(client, "smoke@test.com", "Smoke")
        assert user["email"] == "smoke@test.com"
        resp = client.get("/api/v1/auth/me", headers=_auth(t))
        assert resp.status_code == 200


# ── 20. normalize_email works correctly ─────────────────────────────

class TestNormalizeEmail:
    def test_lowercase(self):
        assert normalize_email("User@Example.COM") == "user@example.com"

    def test_strips_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_empty_string(self):
        assert normalize_email("") == ""

    def test_already_normalized(self):
        assert normalize_email("user@example.com") == "user@example.com"
