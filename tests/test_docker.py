"""Unit tests for app/docker.py."""

import json
from unittest.mock import MagicMock, patch

from app.config import CONFIG
from app.docker import (
    DockerStatus,
    ServiceStatus,
    can_enter_game,
    get_docker_status,
    get_services_status,
    is_docker_running,
    is_wsl_available,
    launch_wow_client,
    start_server,
    stop_server,
)


def test_wsl_available_true():
    with patch("app.docker.run_wsl_command", return_value=(0, "ok", "")):
        assert is_wsl_available() is True


def test_wsl_available_false():
    with patch("app.docker.run_wsl_command", return_value=(1, "", "Error")):
        assert is_wsl_available() is False


def test_docker_running_true():
    with patch("app.docker.run_wsl_command", return_value=(0, "", "")):
        assert is_docker_running() is True


def test_docker_running_false():
    with patch("app.docker.run_wsl_command", return_value=(1, "", "daemon not running")):
        assert is_docker_running() is False


def test_get_docker_status_success():
    def mock_run(cmd, **kwargs):
        if "echo ok" in cmd:
            return 0, "ok", ""
        if "docker info" in cmd:
            return 0, "", ""
        if "docker --version" in cmd:
            return 0, "Docker version 29.7.2, build a7dcaa6", ""
        if "docker compose version" in cmd:
            return 0, "Docker Compose version v5.5.0", ""
        return 0, "", ""

    with patch("app.docker.run_wsl_command", side_effect=mock_run):
        status = get_docker_status()
        assert status.wsl_available is True
        assert status.docker_running is True
        assert "29.7.2" in status.docker_version
        assert "v5.5.0" in status.compose_version


def test_get_services_status_stopped():
    with patch("app.docker.is_docker_running", return_value=True), patch(
        "app.docker.run_wsl_command", return_value=(0, "", "")
    ):
        statuses = get_services_status()
        for svc in CONFIG.core_services:
            assert svc in statuses
            assert statuses[svc].state == "stopped"


def test_get_services_status_running():
    mock_json = json.dumps(
        [
            {
                "Name": "ac-database",
                "Service": "ac-database",
                "State": "running",
                "Status": "Up 10 minutes",
                "Publishers": [{"TargetPort": 3306, "PublishedPort": 3306}],
            },
            {
                "Name": "ac-worldserver",
                "Service": "ac-worldserver",
                "State": "running",
                "Status": "Up 5 minutes",
                "Publishers": [],
            },
            {
                "Name": "ac-authserver",
                "Service": "ac-authserver",
                "State": "running",
                "Status": "Up 5 minutes",
                "Publishers": [],
            },
        ]
    )

    with patch("app.docker.is_docker_running", return_value=True), patch(
        "app.docker.run_wsl_command", return_value=(0, mock_json, "")
    ):
        statuses = get_services_status()
        assert statuses["ac-database"].state == "running"
        assert statuses["ac-worldserver"].state == "running"
        assert statuses["ac-authserver"].state == "running"


def test_start_server_success():
    with patch("app.docker.is_docker_running", return_value=True), patch(
        "app.docker.run_wsl_command", return_value=(0, "Started", "")
    ) as mock_run:
        success, msg = start_server()
        assert success is True
        assert "booted successfully" in msg
        mock_run.assert_called_once()
        assert "docker compose up -d" in mock_run.call_args[0][0]


def test_stop_server_success():
    with patch("app.docker.is_docker_running", return_value=True), patch(
        "app.docker.run_wsl_command", return_value=(0, "Stopped", "")
    ) as mock_run:
        success, msg = stop_server()
        assert success is True
        assert "shut down cleanly" in msg
        mock_run.assert_called_once()
        assert "docker compose down" in mock_run.call_args[0][0]



def test_can_enter_game_blocked_when_containers_stopped():
    with patch("app.docker.is_docker_running", return_value=True), patch(
        "app.docker.get_services_status"
    ) as mock_svc:
        mock_svc.return_value = {
            "ac-database": ServiceStatus("ac-database", "ac-database", "stopped", "Stopped"),
            "ac-authserver": ServiceStatus("ac-authserver", "ac-authserver", "stopped", "Stopped"),
            "ac-worldserver": ServiceStatus("ac-worldserver", "ac-worldserver", "stopped", "Stopped"),
        }
        allowed, reason = can_enter_game()
        assert allowed is False
        assert "not running" in reason


def test_can_enter_game_ready():
    with patch("app.docker.is_docker_running", return_value=True), patch(
        "app.docker.get_services_status"
    ) as mock_svc, patch("app.docker.is_worldserver_ready") as mock_ready:
        mock_svc.return_value = {
            "ac-database": ServiceStatus("ac-database", "ac-database", "running", "Up"),
            "ac-authserver": ServiceStatus("ac-authserver", "ac-authserver", "running", "Up"),
            "ac-worldserver": ServiceStatus("ac-worldserver", "ac-worldserver", "running", "Up"),
        }
        mock_ready.return_value = (True, "Ready")
        allowed, msg = can_enter_game()
        assert allowed is True
        assert "ready for connections" in msg


def test_launch_wow_client_blocked_by_safety_gate():
    with patch("app.docker.can_enter_game", return_value=(False, "Database stopped")):
        success, msg = launch_wow_client(check_readiness=True)
        assert success is False
        assert "Database stopped" in msg
