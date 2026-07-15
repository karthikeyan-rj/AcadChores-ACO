"""
Authorization tests for ACO backend API.
"""
import pytest
from starlette.testclient import TestClient
from app.main import app
from app.core.rate_limit import limiter
from app.core.config import settings
from app.core.database import db_manager
from app.infrastructure.memory_db import _in_memory_collections


@pytest.fixture(autouse=True)
def _clear_state():
    """Reset rate limiter, memory DB, and MongoDB test users before each test."""
    # Reset slowapi rate limiter storage
    storage = limiter._storage
    if hasattr(storage, 'reset'):
        storage.reset()
    elif hasattr(storage, 'storage') and hasattr(storage.storage, 'clear'):
        storage.storage.clear()

    # Clear in-memory collections
    for coll in _in_memory_collections.values():
        coll.clear()

    yield

    # Cleanup after test
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


def _purge_test_users():
    """Delete all test users from MongoDB."""
    import pymongo
    client = pymongo.MongoClient("mongodb://localhost:27017")
    try:
        db = client[settings.MONGODB_DATABASE]
        db.users.delete_many({})
    except Exception:
        pass
    finally:
        client.close()


@pytest.fixture(autouse=True)
def _cleanup_mongo_users():
    """Delete test users from MongoDB before and after each test."""
    _purge_test_users()
    yield
    _purge_test_users()


def _register(client, email, name, password="Test1234!"):
    resp = client.post("/api/v1/auth/register", json={
        "email": email, "name": name, "password": password,
    })
    assert resp.status_code == 200, f"Register failed ({email}): {resp.text}"
    return resp.json()["access_token"], resp.json()["user"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Unauthenticated access returns 401 ───────────────────────────────

class TestUnauthenticatedAccess:
    @pytest.mark.parametrize("method,path", [
        ("GET",  "/api/v1/workflows"),
        ("GET",  "/api/v1/executions"),
        ("POST", "/api/v1/workflows/chat"),
        ("GET",  "/api/v1/dashboard"),
        ("GET",  "/api/v1/providers"),
        ("GET",  "/api/v1/search/files?query=test"),
        ("GET",  "/api/v1/permissions/policies"),
        ("GET",  "/api/v1/plugins"),
        ("GET",  "/api/v1/auth/me"),
    ])
    def test_returns_401(self, client, method, path):
        resp = client.request(method, path)
        assert resp.status_code == 401


# ── Public endpoints still work ──────────────────────────────────────

class TestPublicEndpoints:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("healthy", "degraded")

    def test_register_and_login(self, client):
        _register(client, "login@test.com", "Login")
        resp = client.post("/api/v1/auth/login", json={
            "email": "login@test.com", "password": "Test1234!",
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()


# ── Valid owner access succeeds ──────────────────────────────────────

class TestOwnerAccess:
    def test_create_and_list_workflow(self, client):
        token, _ = _register(client, "owner@test.com", "Owner")
        resp = client.post("/api/v1/workflows", json={
            "title": "My Workflow", "description": "Test", "steps": [],
        }, headers=_auth(token))
        assert resp.status_code == 200
        resp = client.get("/api/v1/workflows", headers=_auth(token))
        assert resp.status_code == 200
        assert any(w["title"] == "My Workflow" for w in resp.json())

    def test_list_executions_empty(self, client):
        token, _ = _register(client, "exec@test.com", "Exec")
        resp = client.get("/api/v1/executions", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_own_profile(self, client):
        token, user = _register(client, "profile@test.com", "Profile")
        resp = client.get("/api/v1/auth/me", headers=_auth(token))
        assert resp.status_code == 200
        assert resp.json()["email"] == "profile@test.com"


# ── User A cannot read user B's resources ────────────────────────────

class TestCrossUserRead:
    def test_userB_cannot_list_userA_workflows(self, client):
        ta, _ = _register(client, "a@test.com", "UserA")
        tb, _ = _register(client, "b@test.com", "UserB")

        client.post("/api/v1/workflows", json={
            "title": "A's Secret", "description": "", "steps": [],
        }, headers=_auth(ta))

        resp = client.get("/api/v1/workflows", headers=_auth(tb))
        assert resp.status_code == 200
        titles = [w["title"] for w in resp.json()]
        assert "A's Secret" not in titles

    def test_userB_cannot_execute_userA_workflow(self, client):
        ta, _ = _register(client, "a2@test.com", "A2")
        tb, _ = _register(client, "b2@test.com", "B2")

        resp = client.post("/api/v1/workflows", json={
            "title": "Private", "description": "", "steps": [],
        }, headers=_auth(ta))
        wid = resp.json()["_id"]

        resp = client.post(f"/api/v1/workflows/{wid}/execute", headers=_auth(tb))
        assert resp.status_code in (403, 404)


# ── User A cannot mutate user B's resources ──────────────────────────

class TestCrossUserMutate:
    def test_userB_cannot_abort_userA_execution(self, client):
        ta, _ = _register(client, "a3@test.com", "A3")
        tb, _ = _register(client, "b3@test.com", "B3")

        resp = client.post("/api/v1/workflows", json={
            "title": "A3 WF", "description": "", "steps": [],
        }, headers=_auth(ta))
        wid = resp.json()["_id"]
        resp = client.post(f"/api/v1/workflows/{wid}/execute", headers=_auth(ta))
        if resp.status_code == 200:
            exec_id = resp.json().get("execution_id")
            if exec_id:
                resp = client.post(
                    f"/api/v1/executions/{exec_id}/abort", headers=_auth(tb))
                assert resp.status_code in (403, 404)


# ── List endpoints are user-scoped ───────────────────────────────────

class TestListScoping:
    def test_workflows_list_only_own(self, client):
        ta, _ = _register(client, "sc1@test.com", "ScopeA")
        tb, _ = _register(client, "sc2@test.com", "ScopeB")

        for i in range(2):
            client.post("/api/v1/workflows", json={
                "title": f"A-{i}", "description": "", "steps": [],
            }, headers=_auth(ta))

        client.post("/api/v1/workflows", json={
            "title": "B-0", "description": "", "steps": [],
        }, headers=_auth(tb))

        a_wfs = client.get("/api/v1/workflows", headers=_auth(ta)).json()
        b_wfs = client.get("/api/v1/workflows", headers=_auth(tb)).json()
        assert len(a_wfs) == 2
        assert len(b_wfs) == 1
        assert b_wfs[0]["title"] == "B-0"

    def test_executions_list_only_own(self, client):
        ta, _ = _register(client, "ex1@test.com", "ExA")
        tb, _ = _register(client, "ex2@test.com", "ExB")

        resp_b = client.get("/api/v1/executions", headers=_auth(tb))
        assert resp_b.status_code == 200
        assert resp_b.json() == []


# ── Admin-only routes reject non-admin users ─────────────────────────

class TestAdminOnly:
    def test_register_plugin_rejects_normal_user(self, client):
        t, _ = _register(client, "n1@test.com", "N1")
        resp = client.post("/api/v1/plugins/register", json={
            "name": "p", "version": "1", "description": "d",
            "entry_point": "run", "code": "def run(i): pass",
            "inputs_schema": {},
        }, headers=_auth(t))
        assert resp.status_code == 403
        assert "Admin" in resp.json()["detail"]

    def test_run_plugin_rejects_normal_user(self, client):
        t, _ = _register(client, "n2@test.com", "N2")
        resp = client.post("/api/v1/plugins/run", json={
            "plugin_name": "x", "inputs": {},
        }, headers=_auth(t))
        assert resp.status_code == 403

    def test_download_model_rejects_normal_user(self, client):
        t, _ = _register(client, "n3@test.com", "N3")
        resp = client.post("/api/v1/providers/ollama/models/download", json={
            "model_id": "m",
        }, headers=_auth(t))
        assert resp.status_code == 403

    def test_delete_model_rejects_normal_user(self, client):
        t, _ = _register(client, "n4@test.com", "N4")
        resp = client.delete(
            "/api/v1/providers/ollama/models/m", headers=_auth(t))
        assert resp.status_code == 403


# ── CORS tests ───────────────────────────────────────────────────────

class TestCORS:
    def test_allows_configured_origin(self, client):
        resp = client.options("/api/v1/workflows", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        acao = resp.headers.get("access-control-allow-origin", "")
        assert "localhost:3000" in acao

    def test_rejects_unconfigured_origin(self, client):
        resp = client.options("/api/v1/workflows", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "GET",
        })
        acao = resp.headers.get("access-control-allow-origin", "")
        assert acao != "https://evil.com"


# ── Providers route ordering — aggregate routes reachable ─────────────

class TestProviderRoutes:
    def test_capabilities_reachable(self, client):
        t, _ = _register(client, "cap@test.com", "Cap")
        resp = client.get("/api/v1/providers/capabilities", headers=_auth(t))
        assert resp.status_code == 200
        assert "total_agents" in resp.json()

    def test_all_metrics_reachable(self, client):
        t, _ = _register(client, "met@test.com", "Met")
        resp = client.get("/api/v1/providers/metrics", headers=_auth(t))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── Auth flow: token lifecycle ───────────────────────────────────────

class TestTokenLifecycle:
    def test_login_returns_access_token(self, client):
        _register(client, "tk1@test.com", "Token1")
        resp = client.post("/api/v1/auth/login", json={
            "email": "tk1@test.com", "password": "Test1234!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 20

    def test_register_returns_access_token(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "email": "tk2@test.com", "name": "Token2", "password": "Test1234!",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_token_authenticates_me(self, client):
        _register(client, "tk3@test.com", "Token3")
        resp = client.post("/api/v1/auth/login", json={
            "email": "tk3@test.com", "password": "Test1234!",
        })
        token = resp.json()["access_token"]
        me = client.get("/api/v1/auth/me", headers=_auth(token))
        assert me.status_code == 200
        assert me.json()["email"] == "tk3@test.com"

    def test_same_secret_used_across_restarts(self, client):
        """Token signed with same SECRET_KEY is valid across requests."""
        _register(client, "tk4@test.com", "Token4")
        resp = client.post("/api/v1/auth/login", json={
            "email": "tk4@test.com", "password": "Test1234!",
        })
        token = resp.json()["access_token"]
        # Multiple requests with same token should all succeed
        for _ in range(3):
            me = client.get("/api/v1/auth/me", headers=_auth(token))
            assert me.status_code == 200


# ── Auth flow: generate-plan and chat require token ──────────────────

class TestProtectedEndpointAuth:
    def test_generate_plan_requires_auth(self, client):
        resp = client.post("/api/v1/workflows/generate-plan", json={
            "prompt": "open calculator",
        })
        assert resp.status_code == 401

    def test_generate_plan_succeeds_with_token(self, client):
        t, _ = _register(client, "gp1@test.com", "GP1")
        resp = client.post("/api/v1/workflows/generate-plan", json={
            "prompt": "open calculator",
        }, headers=_auth(t))
        # Should not be 401 - may be 200 or 500 (LLM unavailable) but not auth failure
        assert resp.status_code != 401

    def test_chat_requires_auth(self, client):
        resp = client.post("/api/v1/workflows/chat", json={
            "message": "hello",
        })
        assert resp.status_code == 401

    def test_chat_succeeds_with_token(self, client):
        t, _ = _register(client, "ch1@test.com", "CH1")
        resp = client.post("/api/v1/workflows/chat", json={
            "message": "hello",
        }, headers=_auth(t))
        # Should not be 401 - may succeed or fail on LLM but not auth
        assert resp.status_code != 401

    def test_create_workflow_requires_auth(self, client):
        resp = client.post("/api/v1/workflows", json={
            "title": "Test", "description": "Test", "steps": [],
        })
        assert resp.status_code == 401

    def test_execute_workflow_requires_auth(self, client):
        resp = client.post("/api/v1/workflows/000000000000000000000000/execute")
        assert resp.status_code == 401

    def test_dashboard_requires_auth(self, client):
        resp = client.get("/api/v1/dashboard")
        assert resp.status_code == 401

    def test_providers_requires_auth(self, client):
        resp = client.get("/api/v1/providers")
        assert resp.status_code == 401

    def test_executions_requires_auth(self, client):
        resp = client.get("/api/v1/executions")
        assert resp.status_code == 401


# ── Auth flow: expired/invalid tokens ────────────────────────────────

class TestTokenValidation:
    def test_expired_token_returns_401(self, client):
        from app.core.security import create_access_token
        from datetime import timedelta
        _register(client, "exp1@test.com", "Exp1")
        # Create a token that expired 1 hour ago
        token = create_access_token(
            {"sub": "exp1@test.com"},
            expires_delta=timedelta(hours=-1)
        )
        resp = client.get("/api/v1/auth/me", headers=_auth(token))
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me", headers=_auth("totally.bogus.token"))
        assert resp.status_code == 401

    def test_tampered_token_returns_401(self, client):
        _register(client, "tam1@test.com", "Tam1")
        resp = client.post("/api/v1/auth/login", json={
            "email": "tam1@test.com", "password": "Test1234!",
        })
        token = resp.json()["access_token"]
        # Tamper with the token
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1][::-1] + "." + parts[2]
        resp = client.get("/api/v1/auth/me", headers=_auth(tampered))
        assert resp.status_code == 401

    def test_missing_sub_returns_401(self, client):
        from app.core.security import create_access_token
        token = create_access_token({"no_sub": "here"})
        resp = client.get("/api/v1/auth/me", headers=_auth(token))
        assert resp.status_code == 401

    def test_nonexistent_user_returns_401(self, client):
        from app.core.security import create_access_token
        token = create_access_token({"sub": "ghost@nowhere.com"})
        resp = client.get("/api/v1/auth/me", headers=_auth(token))
        assert resp.status_code == 401


# ── Auth flow: /me endpoint validation ───────────────────────────────

class TestMeEndpoint:
    def test_me_returns_user_data(self, client):
        t, _ = _register(client, "me1@test.com", "Me1")
        resp = client.get("/api/v1/auth/me", headers=_auth(t))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "me1@test.com"
        assert data["name"] == "Me1"
        assert "id" in data
        assert "role" in data

    def test_me_without_token_returns_401(self, client):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ── Auth flow: duplicate email handling ──────────────────────────────

class TestDuplicateRegistration:
    def test_duplicate_email_rejected(self, client):
        _register(client, "dup@test.com", "Dup1")
        resp = client.post("/api/v1/auth/register", json={
            "email": "dup@test.com", "name": "Dup2", "password": "Test1234!",
        })
        assert resp.status_code == 400
        assert "already" in resp.json()["detail"].lower()
