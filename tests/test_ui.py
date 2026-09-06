"""Unit tests for UI components and theme."""

import sys
import pytest
from PySide6.QtWidgets import QApplication

from app.docker import ServiceStatus
from ui.components.action_bar import ActionBar
from ui.components.header import HeaderBanner
from ui.components.log_viewer import LogViewer
from ui.components.status_panel import StatusPanel
from ui.theme import get_stylesheet


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


def test_theme_stylesheet():
    ss = get_stylesheet()
    assert "background-color" in ss
    assert "HeroEnterGame" in ss


def test_header_banner(qapp):
    header = HeaderBanner()
    assert header.title_label.text() == "AZEROTHCORE MANAGER"
    assert header.version_badge.text() == "v0.1"

    header.update_status(wsl_available=True, docker_running=True)
    assert "Running" in header.docker_badge.text()

    header.update_status(wsl_available=False, docker_running=False)
    assert "Unresponsive" in header.wsl_badge.text()
    assert "Stopped" in header.docker_badge.text()


def test_status_panel(qapp):
    panel = StatusPanel()
    assert panel.card_db.title_label.text() == "Database"
    assert panel.card_auth.title_label.text() == "Authserver"
    assert panel.card_world.title_label.text() == "Worldserver"

    services = {
        "ac-database": ServiceStatus("ac-database", "ac-database", "running", "Up 5m"),
        "ac-authserver": ServiceStatus("ac-authserver", "ac-authserver", "stopped", "Stopped"),
        "ac-worldserver": ServiceStatus("ac-worldserver", "ac-worldserver", "running", "Up 2m"),
    }
    panel.update_services(services, world_ready=True)

    assert panel.card_db.badge.text() == "RUNNING"
    assert panel.card_auth.badge.text() == "STOPPED"
    assert panel.card_world.badge.text() == "READY"


def test_action_bar_readiness_gate(qapp):
    bar = ActionBar()
    assert bar.btn_play.isEnabled() is False

    # When server becomes ready
    bar.set_readiness(True, "Server online")
    assert bar.btn_play.isEnabled() is True
    assert "ready" in bar.gate_label.text().lower()

    # When server is stopped
    bar.set_readiness(False, "Database offline")
    assert bar.btn_play.isEnabled() is False
    assert "Database offline" in bar.gate_label.text()


def test_log_viewer(qapp):
    viewer = LogViewer()
    assert viewer.get_selected_service() == "ac-worldserver"
    assert "Worldserver" in viewer.header_label.text()

    viewer.set_logs("Test AzerothCore log line")
    assert "Test AzerothCore log line" in viewer.terminal.toPlainText()

    viewer.clear_logs()
    assert viewer.terminal.toPlainText() == ""


