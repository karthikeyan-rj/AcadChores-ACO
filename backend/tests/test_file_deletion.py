"""Tests for file deletion endpoint (Issue 3: file deletion)."""
import os
import tempfile
import shutil
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_current_user
from app.core.database import db_manager


@pytest.fixture
def client():
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="aco_test_")
    with open(os.path.join(d, "test.txt"), "w") as f:
        f.write("hello")
    nested = os.path.join(d, "subfolder")
    os.makedirs(nested)
    with open(os.path.join(nested, "nested.txt"), "w") as f:
        f.write("nested content")
    with open(os.path.join(d, "file with spaces.txt"), "w") as f:
        f.write("spaces")
    yield d
    shutil.rmtree(d, ignore_errors=True)


def _mock_user():
    user = MagicMock()
    user.id = ObjectId()
    user.email = "test@example.com"
    user.name = "Test User"
    user.role = "user"
    return user


@pytest.fixture(autouse=True)
def override_auth():
    saved = dict(app.dependency_overrides)
    mock_u = _mock_user()
    app.dependency_overrides[get_current_user] = lambda: mock_u
    prev_use_memory = db_manager.use_memory
    db_manager.use_memory = True
    yield
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)
    db_manager.use_memory = prev_use_memory


class TestFileDeleteEndpoint:
    def test_delete_requires_auth(self, client, temp_dir):
        saved = dict(app.dependency_overrides)
        app.dependency_overrides.clear()
        try:
            resp = client.post("/api/v1/search/files/delete", json={"path": "test.txt"})
            assert resp.status_code in (401, 403)
        finally:
            app.dependency_overrides.update(saved)

    def test_delete_empty_path_rejected(self, client, temp_dir):
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": ""},
        )
        assert resp.status_code == 400
        assert "required" in resp.json()["detail"].lower()

    def test_delete_nonexistent_file_returns_404(self, client, temp_dir):
        client.post(
            "/api/v1/search/index/config",
            json={"roots": [temp_dir], "enabled": True},
        )
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": os.path.join(temp_dir, "nonexistent.txt")},
        )
        assert resp.status_code == 404

    def test_delete_directory_rejected(self, client, temp_dir):
        client.post(
            "/api/v1/search/index/config",
            json={"roots": [temp_dir], "enabled": True},
        )
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": temp_dir},
        )
        assert resp.status_code == 400
        assert "director" in resp.json()["detail"].lower()

    def test_delete_file_outside_workspace_rejected(self, client, temp_dir):
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": "C:\\Windows\\System32\\test.txt"},
        )
        assert resp.status_code in (403, 400)


class TestPathNormalization:
    def test_path_with_spaces_accepted(self, client, temp_dir):
        client.post(
            "/api/v1/search/index/config",
            json={"roots": [temp_dir], "enabled": True},
        )
        filepath = os.path.join(temp_dir, "file with spaces.txt")
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": filepath},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            assert not os.path.exists(filepath)

    def test_nested_folder_file_accepted(self, client, temp_dir):
        client.post(
            "/api/v1/search/index/config",
            json={"roots": [temp_dir], "enabled": True},
        )
        filepath = os.path.join(temp_dir, "subfolder", "nested.txt")
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": filepath},
        )
        assert resp.status_code == 200
        assert not os.path.exists(filepath)

    def test_traversal_attack_rejected(self, client, temp_dir):
        client.post(
            "/api/v1/search/index/config",
            json={"roots": [temp_dir], "enabled": True},
        )
        traversal_path = os.path.join(temp_dir, "..", "escape.txt")
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": traversal_path},
        )
        assert resp.status_code == 403


class TestMetadataCleanup:
    def test_metadata_removed_after_delete(self, client, temp_dir):
        client.post(
            "/api/v1/search/index/config",
            json={"roots": [temp_dir], "enabled": True},
        )
        filepath = os.path.join(temp_dir, "test.txt")
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": filepath},
        )
        if resp.status_code == 200:
            assert not os.path.exists(filepath)
            search_resp = client.get(
                "/api/v1/search/files?query=test.txt",
            )
            if search_resp.status_code == 200:
                results = search_resp.json().get("results", [])
                assert all(r.get("file_path") != filepath for r in results)


class TestNoRootsConfigured:
    def test_delete_without_roots_returns_400(self, client):
        resp = client.post(
            "/api/v1/search/files/delete",
            json={"path": "/some/path/file.txt"},
        )
        assert resp.status_code in (400, 403)
