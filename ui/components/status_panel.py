"""Status panel displaying interactive visual cards for Database, Authserver, and Worldserver."""

from typing import Dict
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.docker import ServiceStatus
from ui.theme import (
    AMBER_WARNING,
    BG_CARD,
    BORDER_ACCENT,
    BORDER_SUBTLE,
    GREEN_BRIGHT,
    GREEN_ONLINE,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class ServiceCard(QFrame):
    """An individual service status card."""

    def __init__(self, title: str, subtitle: str, port_info: str, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.setMinimumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header Row: Title & Badge
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {TEXT_PRIMARY};"
        )
        top_row.addWidget(self.title_label)
        top_row.addStretch()

        self.badge = QLabel("STOPPED")
        self.badge.setProperty("class", "StatusBadge StatusBadgeStopped")
        top_row.addWidget(self.badge)

        layout.addLayout(top_row)

        # Subtitle
        self.sub_label = QLabel(subtitle)
        self.sub_label.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        layout.addWidget(self.sub_label)

        layout.addStretch()

        # Footer Row: Port & Runtime Info
        bottom_row = QHBoxLayout()
        self.port_label = QLabel(f"Port: {port_info}")
        self.port_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; font-weight: 600;")
        bottom_row.addWidget(self.port_label)
        bottom_row.addStretch()

        self.info_label = QLabel("Offline")
        self.info_label.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        bottom_row.addWidget(self.info_label)

        layout.addLayout(bottom_row)

    def set_status(self, state: str, details: str = "", is_special_ready: bool = False):
        state_clean = state.lower()
        if is_special_ready or (state_clean == "running" and "healthy" in details.lower()):
            self.badge.setText("ONLINE" if not is_special_ready else "READY")
            self.badge.setStyleSheet(
                f"background-color: rgba(35, 134, 54, 0.25); color: {GREEN_BRIGHT}; "
                f"border: 1px solid {GREEN_ONLINE}; border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
            )
            self.setStyleSheet(
                f"background-color: {BG_CARD}; border: 1px solid rgba(35, 134, 54, 0.5); border-radius: 10px;"
            )
        elif state_clean == "running":
            self.badge.setText("RUNNING")
            self.badge.setStyleSheet(
                f"background-color: rgba(35, 134, 54, 0.2); color: {GREEN_BRIGHT}; "
                f"border: 1px solid {GREEN_ONLINE}; border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
            )
            self.setStyleSheet(
                f"background-color: {BG_CARD}; border: 1px solid rgba(35, 134, 54, 0.4); border-radius: 10px;"
            )
        elif state_clean in ("starting", "booting"):
            self.badge.setText("STARTING")
            self.badge.setStyleSheet(
                f"background-color: rgba(210, 153, 34, 0.25); color: {AMBER_WARNING}; "
                f"border: 1px solid {AMBER_WARNING}; border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
            )
            self.setStyleSheet(
                f"background-color: {BG_CARD}; border: 1px solid rgba(210, 153, 34, 0.5); border-radius: 10px;"
            )
        else:
            self.badge.setText("STOPPED")
            self.badge.setStyleSheet(
                "background-color: rgba(218, 54, 51, 0.15); color: #ff7b72; "
                "border: 1px solid rgba(218, 54, 51, 0.4); border-radius: 6px; padding: 3px 8px; font-size: 11px; font-weight: bold;"
            )
            self.setStyleSheet(
                f"background-color: {BG_CARD}; border: 1px solid {BORDER_SUBTLE}; border-radius: 10px;"
            )

        self.info_label.setText(details if details else ("Running" if state_clean == "running" else "Offline"))


class StatusPanel(QWidget):
    """Container with cards for Database, Authserver, and Worldserver."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.card_db = ServiceCard("Database", "MySQL 8.4 Server", "3306", self)
        self.card_auth = ServiceCard("Authserver", "Logon & Accounts", "3724", self)
        self.card_world = ServiceCard("Worldserver", "Game Realm & Bots", "8085", self)

        layout.addWidget(self.card_db)
        layout.addWidget(self.card_auth)
        layout.addWidget(self.card_world)

    def update_services(self, services: Dict[str, ServiceStatus], world_ready: bool = False):
        db = services.get("ac-database")
        if db:
            self.card_db.set_status(db.state, db.status)
        else:
            self.card_db.set_status("stopped", "Not running")

        auth = services.get("ac-authserver")
        if auth:
            self.card_auth.set_status(auth.state, auth.status)
        else:
            self.card_auth.set_status("stopped", "Not running")

        world = services.get("ac-worldserver")
        if world:
            if world.state == "running" and not world_ready:
                self.card_world.set_status("booting", "Initializing World...")
            else:
                self.card_world.set_status(world.state, world.status, is_special_ready=world_ready)
        else:
            self.card_world.set_status("stopped", "Not running")
