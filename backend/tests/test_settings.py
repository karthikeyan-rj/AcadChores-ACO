"""
Tests for per-user settings API endpoints.
"""
import pytest
from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient
from app.main import app
from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.database import db_manager
from app.infrastructure.memory_db import _in_memory_collections


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset rate limiter and memory DB before each test."""
    storage = limiter._storage
    if hasattr(storage, 'reset'):
        storage.reset()
    elif hasattr(storage, 'storage') and hasattr(storage.storage, 'clear'):
        storage.storage.clear()
    for coll in _in_memory_collections.values():
        coll.clear()
    yield
    for coll in _in_memory_collections.values():
        coll.clear()
    if hasattr(storage, 'reset'):
        storage.reset()
    elif hasattr(storage, 'storage') and hasattr(storage.storage, 'clear'):
        storage.storage.clear()


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _purge_all():
    """Delete test data from MongoDB."""
    import pymongo
    c = pymongo.MongoClient("mongodb://localhost:27017")
    try:
        db = c[settings.MONGODB_DATABASE]
        db.users.delete_many({})
        db.user_settings.delete_many({})
        db.user_api_keys.delete_many({})
    except Exception:
        pass
    finally:
        c.close()


@pytest.fixture(autouse=True)
def _cleanup():
    _purge_all()
    yield
    _purge_all()


def _register(client, email="s@test.com", name="S", password="Test1234!"):
    resp = client.post("/api/v1/auth/register", json={
        "email": email, "name": name, "password": password,
    })
    assert resp.status_code == 200, f"Register failed: {resp.text}"
    return resp.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── 1. Unauthenticated returns 401 ──────────────────────────────────

class TestUnauthenticated:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/v1/settings"),
        ("PATCH", "/api/v1/settings"),
        ("GET", "/api/v1/settings/api-keys"),
        ("POST", "/api/v1/settings/api-keys"),
    ])
    def test_returns_401(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401


# ── 2. Default settings ──────────────────────────────────────────────

class TestDefaults:
    def test_new_user_gets_defaults(self, client):
        token = _register(client)
        resp = client.get("/api/v1/settings", headers=_auth(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_fallback_enabled"] is False
        assert data["cloud_provider"] == "openai"
        assert data["cloud_model"] == "gpt-4o-mini"
        assert data["workflow_quality_threshold"] == 70
        assert data["local_planner_retry_count"] == 1
        assert data["api_key_configured"] is False


# ── 3. Update settings ───────────────────────────────────────────────

class TestUpdate:
    def test_update_fields(self, client):
        token = _register(client, "u1@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "cloud_fallback_enabled": True,
            "cloud_provider": "anthropic",
            "cloud_model": "claude-3-5-sonnet-20241022",
            "workflow_quality_threshold": 80,
            "local_planner_retry_count": 2,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_fallback_enabled"] is True
        assert data["cloud_provider"] == "anthropic"
        assert data["cloud_model"] == "claude-3-5-sonnet-20241022"
        assert data["workflow_quality_threshold"] == 80
        assert data["local_planner_retry_count"] == 2

    def test_partial_update_preserves_others(self, client):
        token = _register(client, "u2@test.com")
        # First update
        client.patch("/api/v1/settings", headers=_auth(token), json={
            "cloud_fallback_enabled": True,
            "workflow_quality_threshold": 85,
        })
        # Partial update — only change provider
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "cloud_provider": "gemini",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_provider"] == "gemini"
        assert data["cloud_fallback_enabled"] is True  # preserved
        assert data["workflow_quality_threshold"] == 85  # preserved

    def test_empty_update_rejected(self, client):
        token = _register(client, "u3@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={})
        assert resp.status_code == 400


# ── 4. Validation ────────────────────────────────────────────────────

class TestValidation:
    def test_invalid_provider_rejected(self, client):
        token = _register(client, "v1@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "cloud_provider": "invalid",
        })
        assert resp.status_code == 422

    def test_quality_below_min_rejected(self, client):
        token = _register(client, "v2@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "workflow_quality_threshold": 30,
        })
        assert resp.status_code == 422

    def test_quality_above_max_rejected(self, client):
        token = _register(client, "v3@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "workflow_quality_threshold": 150,
        })
        assert resp.status_code == 422

    def test_retry_count_too_high_rejected(self, client):
        token = _register(client, "v4@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "local_planner_retry_count": 10,
        })
        assert resp.status_code == 422

    def test_retry_count_negative_rejected(self, client):
        token = _register(client, "v5@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "local_planner_retry_count": -1,
        })
        assert resp.status_code == 422

    def test_boundary_quality_min(self, client):
        token = _register(client, "v6@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "workflow_quality_threshold": 50,
        })
        assert resp.status_code == 200

    def test_boundary_quality_max(self, client):
        token = _register(client, "v7@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "workflow_quality_threshold": 100,
        })
        assert resp.status_code == 200

    def test_boundary_retry_zero(self, client):
        token = _register(client, "v8@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "local_planner_retry_count": 0,
        })
        assert resp.status_code == 200

    def test_boundary_retry_max(self, client):
        token = _register(client, "v9@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "local_planner_retry_count": 3,
        })
        assert resp.status_code == 200


# ── 5. User isolation ────────────────────────────────────────────────

class TestIsolation:
    def test_user_a_cannot_see_user_b_settings(self, client):
        token_a = _register(client, "a@test.com", "UserA")
        token_b = _register(client, "b@test.com", "UserB")

        # User A updates settings
        client.patch("/api/v1/settings", headers=_auth(token_a), json={
            "cloud_fallback_enabled": True,
            "cloud_provider": "anthropic",
        })

        # User B should still see defaults
        resp = client.get("/api/v1/settings", headers=_auth(token_b))
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_fallback_enabled"] is False
        assert data["cloud_provider"] == "openai"

    def test_user_a_update_does_not_affect_user_b(self, client):
        token_a = _register(client, "c@test.com", "UserC")
        token_b = _register(client, "d@test.com", "UserD")

        client.patch("/api/v1/settings", headers=_auth(token_a), json={
            "cloud_fallback_enabled": True,
        })
        client.patch("/api/v1/settings", headers=_auth(token_b), json={
            "cloud_fallback_enabled": False,
        })

        # Verify user A is still True
        resp_a = client.get("/api/v1/settings", headers=_auth(token_a))
        assert resp_a.json()["cloud_fallback_enabled"] is True

        # Verify user B is still False
        resp_b = client.get("/api/v1/settings", headers=_auth(token_b))
        assert resp_b.json()["cloud_fallback_enabled"] is False


# ── 6. Persistence ───────────────────────────────────────────────────

class TestPersistence:
    def test_settings_persist_across_requests(self, client):
        token = _register(client, "p@test.com")
        client.patch("/api/v1/settings", headers=_auth(token), json={
            "cloud_fallback_enabled": True,
            "cloud_provider": "gemini",
            "workflow_quality_threshold": 90,
        })

        # Second request should return updated values
        resp = client.get("/api/v1/settings", headers=_auth(token))
        data = resp.json()
        assert data["cloud_fallback_enabled"] is True
        assert data["cloud_provider"] == "gemini"
        assert data["workflow_quality_threshold"] == 90


# ── 7. API key management ────────────────────────────────────────────

class TestApiKeyManagement:
    def test_save_and_retrieve_key(self, client):
        token = _register(client, "k1@test.com")
        resp = client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": "sk-test1234567890abcdef",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["provider"] == "openai"
        assert "••••" in resp.json()["key_hint"]

    def test_key_not_returned_in_settings(self, client):
        token = _register(client, "k2@test.com")
        client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": "sk-test1234567890abcdef",
        })
        resp = client.get("/api/v1/settings", headers=_auth(token))
        data = resp.json()
        assert data["api_key_configured"] is True
        assert "sk-" not in (data.get("api_key_hint") or "")

    def test_delete_key(self, client):
        token = _register(client, "k3@test.com")
        client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": "sk-test1234567890abcdef",
        })
        resp = client.delete("/api/v1/settings/api-keys/openai", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify key is gone
        resp = client.get("/api/v1/settings", headers=_auth(token))
        assert resp.json()["api_key_configured"] is False

    def test_delete_nonexistent_key_returns_404(self, client):
        token = _register(client, "k4@test.com")
        resp = client.delete("/api/v1/settings/api-keys/nonexistent", headers=_auth(token))
        assert resp.status_code == 404

    def test_invalid_provider_rejected(self, client):
        token = _register(client, "k5@test.com")
        resp = client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "invalid",
            "api_key": "sk-test1234567890abcdef",
        })
        assert resp.status_code == 400

    def test_short_key_rejected(self, client):
        token = _register(client, "k6@test.com")
        resp = client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": "short",
        })
        assert resp.status_code == 400

    def test_key_encrypted_in_storage(self, client):
        """Verify the raw key is not stored in plaintext."""
        import pymongo
        token = _register(client, "k7@test.com")
        raw_key = "sk-test1234567890abcdef1234567890"
        client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": raw_key,
        })
        mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
        try:
            db = mongo_client[settings.MONGODB_DATABASE]
            doc = db.user_api_keys.find_one({"provider": "openai"})
            assert doc is not None
            assert doc["encrypted_key"] != raw_key
            assert raw_key not in doc["encrypted_key"]
        finally:
            mongo_client.close()

    def test_key_replacement(self, client):
        token = _register(client, "k8@test.com")
        # Save first key
        client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": "sk-firstkey1234567890abcdef",
        })
        # Replace with second key
        resp = client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "openai",
            "api_key": "sk-secondkey1234567890abcdef",
        })
        assert resp.status_code == 200
        assert "••••" in resp.json()["key_hint"]
        assert resp.json()["key_hint"].endswith("cdef")


# ── 8. Unknown fields rejected ───────────────────────────────────────

class TestUnknownFields:
    def test_unknown_field_rejected(self, client):
        token = _register(client, "u@test.com")
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "unknown_field": "value",
        })
        assert resp.status_code == 422


# ── 9. Settings page loads correctly (manual validation proxy) ──────

class TestSettingsEndpointIntegration:
    def test_full_workflow(self, client):
        """Simulate the full settings page flow: load → update → save → reload."""
        token = _register(client, "w@test.com")

        # 1. Load defaults
        resp = client.get("/api/v1/settings", headers=_auth(token))
        assert resp.status_code == 200
        defaults = resp.json()

        # 2. Update
        resp = client.patch("/api/v1/settings", headers=_auth(token), json={
            "cloud_fallback_enabled": True,
            "cloud_provider": "anthropic",
            "workflow_quality_threshold": 85,
        })
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["cloud_fallback_enabled"] is True
        assert updated["cloud_provider"] == "anthropic"
        assert updated["workflow_quality_threshold"] == 85
        assert updated["local_planner_retry_count"] == defaults["local_planner_retry_count"]

        # 3. Add API key
        resp = client.post("/api/v1/settings/api-keys", headers=_auth(token), json={
            "provider": "anthropic",
            "api_key": "sk-ant-test1234567890abcdef",
        })
        assert resp.status_code == 200

        # 4. Reload — verify all persisted
        resp = client.get("/api/v1/settings", headers=_auth(token))
        data = resp.json()
        assert data["cloud_fallback_enabled"] is True
        assert data["cloud_provider"] == "anthropic"
        assert data["workflow_quality_threshold"] == 85
        assert data["api_key_configured"] is True

        # 5. Delete key
        resp = client.delete("/api/v1/settings/api-keys/anthropic", headers=_auth(token))
        assert resp.status_code == 200

        # 6. Reload — key gone
        resp = client.get("/api/v1/settings", headers=_auth(token))
        assert resp.json()["api_key_configured"] is False
