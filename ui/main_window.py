"""Main application window for AzerothCore Manager."""

import time
from typing import Dict, Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.config import CONFIG
from app.docker import (
    DockerStatus,
    ServiceStatus,
    can_enter_game,
    get_docker_status,
    get_services_status,
    launch_wow_client,
    start_server,
    stop_server,
)
from app.logs import get_container_logs
from ui.components.action_bar import ActionBar
from ui.components.config_view import ConfigView
from ui.components.db_view import DbView
from ui.components.header import HeaderBanner
from ui.components.log_viewer import LogViewer
from ui.components.sidebar import Sidebar
from ui.components.status_panel import StatusPanel
from ui.components.terminal_view import TerminalView
from ui.theme import get_stylesheet


class StatusPollWorker(QThread):
    """Background thread that non-intrusively inspects Docker and server status."""

    status_ready = Signal(object, dict, bool, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self._current_service = "ac-worldserver"
        self._force_event = False


    def set_target_service(self, service_name: str):
        self._current_service = service_name
        self._force_event = True

    def trigger_immediate_poll(self):
        self._force_event = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                docker_status = get_docker_status()
                services = get_services_status()
                ready, reason = can_enter_game()
                _, logs = get_container_logs(self._current_service, tail=120)

                self.status_ready.emit(docker_status, services, ready, reason, logs)
            except Exception:
                # Never crash the poller thread
                pass


            # Sleep in small increments to respond quickly to trigger_immediate_poll or stop
            for _ in range(30):
                if not self._running or self._force_event:
                    self._force_event = False
                    break
                time.sleep(0.1)


class ServerActionWorker(QThread):
    """Background thread that executes start or stop operations safely."""

    action_completed = Signal(str, bool, str)  # action_name, success, message

    def __init__(self, action: str, parent=None):
        super().__init__(parent)
        self.action = action

    def run(self):
        if self.action == "start":
            success, msg = start_server()
        elif self.action == "stop":
            success, msg = stop_server()
        else:
            success, msg = False, f"Unknown action: {self.action}"

        self.action_completed.emit(self.action, success, msg)


class MainWindow(QMainWindow):
    """AzerothCore Manager primary desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AzerothCore Manager - WoW 3.3.5a")
        self.resize(1180, 780)
        self.setMinimumSize(1020, 680)

        # Apply Global Styling
        self.setStyleSheet(get_stylesheet())

        self.init_ui()
        self.init_threads()

    def init_ui(self):
        root_widget = QWidget()
        self.setCentralWidget(root_widget)

        root_layout = QHBoxLayout(root_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Left Sidebar Navigation
        self.sidebar = Sidebar(self)
        self.sidebar.page_changed.connect(self.on_nav_page_changed)
        root_layout.addWidget(self.sidebar)

        # 2. Right Stacked Container
        self.stacked_widget = QStackedWidget(self)

        # --- PAGE 0: Server & Launcher Dashboard ---
        server_page = QWidget()
        server_layout = QVBoxLayout(server_page)
        server_layout.setContentsMargins(18, 16, 18, 16)
        server_layout.setSpacing(14)

        self.header = HeaderBanner(self)
        server_layout.addWidget(self.header)

        self.status_panel = StatusPanel(self)
        server_layout.addWidget(self.status_panel)

        self.action_bar = ActionBar(self)
        self.action_bar.start_requested.connect(self.on_boot_requested)
        self.action_bar.stop_requested.connect(self.on_stop_requested)
        self.action_bar.play_requested.connect(self.on_play_requested)
        server_layout.addWidget(self.action_bar)

        self.log_viewer = LogViewer(self)
        self.log_viewer.refresh_requested.connect(self.on_log_service_changed)
        server_layout.addWidget(self.log_viewer)

        self.stacked_widget.addWidget(server_page)

        # --- PAGE 1: Game Configuration Center ---
        self.config_view = ConfigView(self)
        self.stacked_widget.addWidget(self.config_view)

        # --- PAGE 2: Live Database Explorer & Editor ---
        self.db_view = DbView(self)
        self.stacked_widget.addWidget(self.db_view)

        # --- PAGE 3: WSL Interactive Terminal ---
        self.terminal_view = TerminalView(self)
        self.stacked_widget.addWidget(self.terminal_view)

        root_layout.addWidget(self.stacked_widget)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Monitoring server status...")

    def on_nav_page_changed(self, idx: int):
        self.stacked_widget.setCurrentIndex(idx)
        if idx == 2:
            self.db_view.check_connection_and_init()
        elif idx == 3:
            self.terminal_view.ensure_running()

    def init_threads(self):
        self.poll_worker = StatusPollWorker(self)
        self.poll_worker.status_ready.connect(self.on_status_updated)
        self.poll_worker.start()

        self.action_worker: Optional[ServerActionWorker] = None

    def on_status_updated(
        self,
        docker_status: DockerStatus,
        services: Dict[str, ServiceStatus],
        ready: bool,
        reason: str,
        logs: str,
    ):
        # Update Header
        self.header.update_status(
            docker_status.wsl_available,
            docker_status.docker_running,
            docker_status.docker_version,
        )

        # Update Service Cards
        self.status_panel.update_services(services, world_ready=ready)

        # Update Enter Game Action & Readiness Gate
        self.action_bar.set_readiness(ready, reason)

        # Update Logs Console
        self.log_viewer.set_logs(logs)

    def on_log_service_changed(self, service_name: str):
        self.poll_worker.set_target_service(service_name)

    def on_boot_requested(self):
        self.action_bar.set_server_busy(True, "Booting server containers in background...")
        self.status_bar.showMessage("Starting Docker Compose services (ac-database, ac-authserver, ac-worldserver)...")

        self.action_worker = ServerActionWorker("start", self)
        self.action_worker.action_completed.connect(self.on_action_finished)
        self.action_worker.start()

    def on_stop_requested(self):
        # Gentle user confirmation
        reply = QMessageBox.question(
            self,
            "Shut Off Server",
            "Are you sure you want to stop the server?\n\n"
            "This will safely stop all containers without deleting any data.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.action_bar.set_server_busy(True, "Shutting off server containers safely...")
        self.status_bar.showMessage("Stopping server containers (preserving database and all state)...")

        self.action_worker = ServerActionWorker("stop", self)
        self.action_worker.action_completed.connect(self.on_action_finished)
        self.action_worker.start()

    def on_action_finished(self, action: str, success: bool, msg: str):
        self.action_bar.set_server_busy(False)
        if success:
            self.status_bar.showMessage(f"Action '{action}' finished: {msg}", 8000)
        else:
            self.status_bar.showMessage(f"Action '{action}' encountered an issue: {msg}", 10000)
            QMessageBox.warning(self, "Server Operation Notice", msg)

        # Trigger immediate poll to update cards instantly
        self.poll_worker.trigger_immediate_poll()

    def on_play_requested(self):
        success, msg = launch_wow_client(check_readiness=True)
        if success:
            self.status_bar.showMessage(f"WoW client launched: {msg}", 10000)
        else:
            QMessageBox.warning(self, "Cannot Enter Game", msg)

    def closeEvent(self, event):
        """Clean shutdown of background threads on window exit."""
        if hasattr(self, "poll_worker") and self.poll_worker.isRunning():
            self.poll_worker.stop()
            if not self.poll_worker.wait(1500):
                self.poll_worker.terminate()
        if hasattr(self, "action_worker") and self.action_worker and self.action_worker.isRunning():
            if not self.action_worker.wait(1500):
                self.action_worker.terminate()
        if hasattr(self, "db_view") and hasattr(self.db_view, "query_worker") and self.db_view.query_worker and self.db_view.query_worker.isRunning():
            if not self.db_view.query_worker.wait(1000):
                self.db_view.query_worker.terminate()
        if hasattr(self, "terminal_view"):
            self.terminal_view.stop_shell()
        event.accept()

