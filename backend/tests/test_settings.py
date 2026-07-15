"""
Tests for per-user settings API endpoints.

Uses dependency_overrides for auth; endpoints handle memory mode natively.
"""
import pytest
from unittest.mock import MagicMock
from bson import ObjectId
from starlette.testclient import TestClient
from app.main import app
from app.core.rate_limit import limiter
from app.core.database import db_manager
from app.api.deps import get_current_user
from app.infrastructure.memory_db import _in_memory_collections


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MOCK_USER_ID = str(ObjectId())
MOCK_USER = MagicMock()
MOCK_USER.id = MOCK_USER_ID
MOCK_USER.email = "test@test.com"
MOCK_USER.name = "Test"
MOCK_USER.role = "user"


@pytest.fixture(autouse=True)
def _clear_state():
    storage = limiter._storage
    if hasattr(storage, 'reset'):
        storage.reset()
    elif hasattr(storage, 'storage') and hasattr(storage.storage, 'clear'):
        storage.storage.clear()
    for coll in _in_memory_collections.values():
        coll.clear()
    prev_overrides = dict(app.dependency_overrides)
    yield
    for coll in _in_memory_collections.values():
        coll.clear()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(prev_overrides)
    if hasattr(storage, 'reset'):
        storage.reset()
    elif hasattr(storage, 'storage') and hasattr(storage.storage, 'clear'):
        storage.storage.clear()


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user] = lambda: MOCK_USER
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# 1. Unauthenticated returns 401
# ---------------------------------------------------------------------------

class TestUnauthenticated:
    @pytest.mark.parametrize("method,path", [
        ("GET", "/api/v1/settings"),
        ("PATCH", "/api/v1/settings"),
        ("GET", "/api/v1/settings/api-keys"),
        ("POST", "/api/v1/settings/api-keys"),
    ])
    def test_returns_401(self, method, path):
        with TestClient(app, raise_server_exceptions=True) as c:
            resp = c.request(method, path)
            assert resp.status_code == 401


# ---------------------------------------------------------------------------
# 2. Default settings
# ---------------------------------------------------------------------------

class TestDefaults:
    def test_new_user_gets_defaults(self, client):
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_fallback_enabled"] is False
        assert data["cloud_provider"] == "openai"
        assert data["cloud_model"] == "gpt-4o-mini"
        assert data["workflow_quality_threshold"] == 70
        assert data["local_planner_retry_count"] == 1
        assert data["api_key_configured"] is False


# ---------------------------------------------------------------------------
# 3. Update settings
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_fields(self, client):
        resp = client.patch("/api/v1/settings", json={
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
        client.patch("/api/v1/settings", json={
            "cloud_fallback_enabled": True,
            "workflow_quality_threshold": 85,
        })
        resp = client.patch("/api/v1/settings", json={
            "cloud_provider": "gemini",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_provider"] == "gemini"
        assert data["cloud_fallback_enabled"] is True
        assert data["workflow_quality_threshold"] == 85

    def test_empty_update_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 4. Validation
# ---------------------------------------------------------------------------

class TestValidation:
    def test_invalid_provider_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={"cloud_provider": "invalid"})
        assert resp.status_code == 422

    def test_quality_below_min_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={"workflow_quality_threshold": 30})
        assert resp.status_code == 422

    def test_quality_above_max_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={"workflow_quality_threshold": 150})
        assert resp.status_code == 422

    def test_retry_count_too_high_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={"local_planner_retry_count": 10})
        assert resp.status_code == 422

    def test_retry_count_negative_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={"local_planner_retry_count": -1})
        assert resp.status_code == 422

    def test_boundary_quality_min(self, client):
        resp = client.patch("/api/v1/settings", json={"workflow_quality_threshold": 50})
        assert resp.status_code == 200

    def test_boundary_quality_max(self, client):
        resp = client.patch("/api/v1/settings", json={"workflow_quality_threshold": 100})
        assert resp.status_code == 200

    def test_boundary_retry_zero(self, client):
        resp = client.patch("/api/v1/settings", json={"local_planner_retry_count": 0})
        assert resp.status_code == 200

    def test_boundary_retry_max(self, client):
        resp = client.patch("/api/v1/settings", json={"local_planner_retry_count": 3})
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. User isolation
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_user_a_cannot_see_user_b_settings(self, client):
        client.patch("/api/v1/settings", json={
            "cloud_fallback_enabled": True,
            "cloud_provider": "anthropic",
        })

        other_user = MagicMock()
        other_user.id = str(ObjectId())
        other_user.email = "other@test.com"
        other_user.name = "Other"
        other_user.role = "user"
        app.dependency_overrides[get_current_user] = lambda: other_user

        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cloud_fallback_enabled"] is False
        assert data["cloud_provider"] == "openai"

    def test_user_a_update_does_not_affect_user_b(self, client):
        client.patch("/api/v1/settings", json={"cloud_fallback_enabled": True})

        other_user = MagicMock()
        other_user.id = str(ObjectId())
        other_user.email = "other2@test.com"
        other_user.name = "Other2"
        other_user.role = "user"
        app.dependency_overrides[get_current_user] = lambda: other_user
        client.patch("/api/v1/settings", json={"cloud_fallback_enabled": False})

        app.dependency_overrides[get_current_user] = lambda: MOCK_USER
        resp_a = client.get("/api/v1/settings")
        assert resp_a.json()["cloud_fallback_enabled"] is True

        app.dependency_overrides[get_current_user] = lambda: other_user
        resp_b = client.get("/api/v1/settings")
        assert resp_b.json()["cloud_fallback_enabled"] is False


# ---------------------------------------------------------------------------
# 6. Persistence
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_settings_persist_across_requests(self, client):
        client.patch("/api/v1/settings", json={
            "cloud_fallback_enabled": True,
            "cloud_provider": "gemini",
            "workflow_quality_threshold": 90,
        })
        resp = client.get("/api/v1/settings")
        data = resp.json()
        assert data["cloud_fallback_enabled"] is True
        assert data["cloud_provider"] == "gemini"
        assert data["workflow_quality_threshold"] == 90


# ---------------------------------------------------------------------------
# 7. API key management
# ---------------------------------------------------------------------------

class TestApiKeyManagement:
    def test_save_and_retrieve_key(self, client):
        resp = client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": "sk-test1234567890abcdef",
        })
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["provider"] == "openai"
        assert "••••" in resp.json()["key_hint"]

    def test_key_not_returned_in_settings(self, client):
        client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": "sk-test1234567890abcdef",
        })
        resp = client.get("/api/v1/settings")
        data = resp.json()
        assert data["api_key_configured"] is True
        assert "sk-" not in (data.get("api_key_hint") or "")

    def test_delete_key(self, client):
        client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": "sk-test1234567890abcdef",
        })
        resp = client.delete("/api/v1/settings/api-keys/openai")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        resp = client.get("/api/v1/settings")
        assert resp.json()["api_key_configured"] is False

    def test_delete_nonexistent_key_returns_404(self, client):
        resp = client.delete("/api/v1/settings/api-keys/nonexistent")
        assert resp.status_code == 404

    def test_invalid_provider_rejected(self, client):
        resp = client.post("/api/v1/settings/api-keys", json={
            "provider": "invalid",
            "api_key": "sk-test1234567890abcdef",
        })
        assert resp.status_code == 400

    def test_short_key_rejected(self, client):
        resp = client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": "short",
        })
        assert resp.status_code == 400

    def test_key_encrypted_in_storage(self, client):
        raw_key = "sk-test1234567890abcdef1234567890"
        client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": raw_key,
        })
        docs = _in_memory_collections["user_api_keys"]
        assert len(docs) == 1
        stored = list(docs.values())[0]
        assert stored["encrypted_key"] != raw_key
        assert raw_key not in stored["encrypted_key"]

    def test_key_replacement(self, client):
        client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": "sk-firstkey1234567890abcdef",
        })
        resp = client.post("/api/v1/settings/api-keys", json={
            "provider": "openai",
            "api_key": "sk-secondkey1234567890abcdef",
        })
        assert resp.status_code == 200
        assert "••••" in resp.json()["key_hint"]
        assert resp.json()["key_hint"].endswith("cdef")


# ---------------------------------------------------------------------------
# 8. Unknown fields rejected
# ---------------------------------------------------------------------------

class TestUnknownFields:
    def test_unknown_field_rejected(self, client):
        resp = client.patch("/api/v1/settings", json={"unknown_field": "value"})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# 9. Full workflow integration
# ---------------------------------------------------------------------------

class TestSettingsEndpointIntegration:
    def test_full_workflow(self, client):
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        defaults = resp.json()

        resp = client.patch("/api/v1/settings", json={
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

        resp = client.post("/api/v1/settings/api-keys", json={
            "provider": "anthropic",
            "api_key": "sk-ant-test1234567890abcdef",
        })
        assert resp.status_code == 200

        resp = client.get("/api/v1/settings")
        data = resp.json()
        assert data["cloud_fallback_enabled"] is True
        assert data["cloud_provider"] == "anthropic"
        assert data["workflow_quality_threshold"] == 85
        assert data["api_key_configured"] is True

        resp = client.delete("/api/v1/settings/api-keys/anthropic")
        assert resp.status_code == 200

        resp = client.get("/api/v1/settings")
        assert resp.json()["api_key_configured"] is False
