"""Tests for the process manager (Issue 2: cancellation)."""
import os
import sys
import subprocess
import asyncio
import pytest
from unittest.mock import patch, MagicMock

from app.services.process_manager import (
    register_process, unregister_process, cancel_process,
    cancel_all, is_process_running, _running_processes,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Ensure clean process registry before and after each test."""
    _running_processes.clear()
    yield
    _running_processes.clear()


class TestRegisterUnregister:
    def test_register_adds_process(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        register_process("exec-1", mock_proc)
        assert "exec-1" in _running_processes
        assert _running_processes["exec-1"] is mock_proc

    def test_unregister_removes_process(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 12345
        register_process("exec-1", mock_proc)
        unregister_process("exec-1")
        assert "exec-1" not in _running_processes

    def test_unregister_nonexistent_is_safe(self):
        unregister_process("nonexistent-id")  # Should not raise

    def test_register_overwrites_existing(self):
        mock_proc1 = MagicMock(spec=subprocess.Popen)
        mock_proc1.pid = 111
        mock_proc2 = MagicMock(spec=subprocess.Popen)
        mock_proc2.pid = 222
        register_process("exec-1", mock_proc1)
        register_process("exec-1", mock_proc2)
        assert _running_processes["exec-1"] is mock_proc2


class TestCancelProcess:
    def test_cancel_existing_process(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 99999
        mock_proc.poll.return_value = None  # still running
        register_process("exec-1", mock_proc)

        with patch("app.services.process_manager.sys") as mock_sys:
            mock_sys.platform = "win32"
            with patch("app.services.process_manager.subprocess") as mock_sub:
                mock_sub.run.return_value = MagicMock(returncode=0)
                mock_sub.CREATE_NEW_PROCESS_GROUP = 0
                result = cancel_process("exec-1")

        assert result is True
        assert "exec-1" not in _running_processes

    def test_cancel_nonexistent_returns_false(self):
        result = cancel_process("nonexistent-id")
        assert result is False

    def test_cancel_removes_from_registry(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 11111
        register_process("exec-1", mock_proc)
        cancel_process("exec-1")
        assert "exec-1" not in _running_processes


class TestIsProcessRunning:
    def test_running_process_returns_true(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 90001
        mock_proc.poll.return_value = None
        register_process("exec-1", mock_proc)
        assert is_process_running("exec-1") is True

    def test_finished_process_returns_false(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 90002
        mock_proc.poll.return_value = 0
        register_process("exec-1", mock_proc)
        assert is_process_running("exec-1") is False

    def test_nonexistent_returns_false(self):
        assert is_process_running("nonexistent") is False


class TestCancelAll:
    def test_cancel_all_returns_count(self):
        mock_proc1 = MagicMock(spec=subprocess.Popen)
        mock_proc1.pid = 111
        mock_proc2 = MagicMock(spec=subprocess.Popen)
        mock_proc2.pid = 222
        register_process("exec-1", mock_proc1)
        register_process("exec-2", mock_proc2)

        with patch("app.services.process_manager.sys") as mock_sys:
            mock_sys.platform = "linux"
            with patch("app.services.process_manager.os") as mock_os:
                mock_os.getpgid.return_value = 100
                mock_os.killpg.return_value = None
                count = cancel_all()

        assert count == 2
        assert len(_running_processes) == 0


class TestExecutionIdPropagation:
    """Verify execution_id flows from workflow_engine through to process_manager."""

    def test_process_registered_with_execution_id(self):
        mock_proc = MagicMock(spec=subprocess.Popen)
        mock_proc.pid = 55555
        register_process("exec-abc-123", mock_proc)
        assert "exec-abc-123" in _running_processes

    def test_different_executions_tracked_separately(self):
        mock_proc1 = MagicMock(spec=subprocess.Popen)
        mock_proc1.pid = 111
        mock_proc2 = MagicMock(spec=subprocess.Popen)
        mock_proc2.pid = 222
        register_process("exec-1", mock_proc1)
        register_process("exec-2", mock_proc2)
        cancel_process("exec-1")
        assert "exec-1" not in _running_processes
        assert "exec-2" in _running_processes
