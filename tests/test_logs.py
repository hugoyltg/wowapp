"""Unit tests for app/logs.py."""

from unittest.mock import MagicMock, patch

from app.logs import get_container_logs, is_worldserver_ready


def test_get_container_logs_success():
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "Server started\nListening on port 8085"
    mock_res.stderr = ""

    with patch("subprocess.run", return_value=mock_res):
        success, logs = get_container_logs("ac-worldserver", tail=50)
        assert success is True
        assert "Listening on port 8085" in logs


def test_get_container_logs_failure():
    mock_res = MagicMock()
    mock_res.returncode = 1
    mock_res.stdout = ""
    mock_res.stderr = "No such container: ac-worldserver"

    with patch("subprocess.run", return_value=mock_res):
        success, msg = get_container_logs("ac-worldserver", tail=50)
        assert success is False
        assert "Could not read logs" in msg
        assert "No such container" in msg


def test_is_worldserver_ready_positive():
    sample_logs = """
    Loading Map 0
    Loading Scripts
    AzerothCore rev. b12345 ready for connections!
    """
    with patch("app.logs.get_container_logs", return_value=(True, sample_logs)):
        ready, msg = is_worldserver_ready()
        assert ready is True
        assert "ready for connections" in msg


def test_is_worldserver_ready_booting():
    sample_logs = """
    Loading Spells...
    Loading Creatures...
    """
    with patch("app.logs.get_container_logs", return_value=(True, sample_logs)):
        ready, msg = is_worldserver_ready()
        assert ready is False
        assert "still booting" in msg
