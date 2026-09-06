"""Header banner component displaying app branding, version, and host environment badge."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from app.config import CONFIG
from ui.theme import (
    BORDER_SUBTLE,
    GOLD_PRIMARY,
    GREEN_BRIGHT,
    RED_DANGER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class HeaderBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeaderBanner")
        self.setProperty("class", "HeaderCard")
        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Left Column: Titles & Tagline
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        # Game & App Title
        self.title_label = QLabel("AZEROTHCORE MANAGER")
        self.title_label.setStyleSheet(
            f"font-size: 20px; font-weight: 800; color: {TEXT_PRIMARY}; letter-spacing: 1px;"
        )
        title_row.addWidget(self.title_label)

        # Milestone Badge
        self.version_badge = QLabel("v0.1")
        self.version_badge.setStyleSheet(
            f"background-color: rgba(245, 172, 56, 0.2); color: {GOLD_PRIMARY}; "
            f"border: 1px solid {GOLD_PRIMARY}; border-radius: 4px; padding: 2px 8px; font-size: 11px; font-weight: bold;"
        )
        title_row.addWidget(self.version_badge)
        title_row.addStretch()

        left_layout.addLayout(title_row)

        self.subtitle_label = QLabel("Wrath of the Lich King 3.3.5a Server Controller")
        self.subtitle_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY};")
        left_layout.addWidget(self.subtitle_label)

        layout.addLayout(left_layout)
        layout.addStretch()

        # Right Column: Environment Badges
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        right_layout.setSpacing(6)

        self.wsl_badge = QLabel("WSL 2: Ubuntu-24.04")
        self.wsl_badge.setStyleSheet(
            f"color: {TEXT_SECONDARY}; font-size: 11px; font-weight: 600; "
            f"background: rgba(35, 47, 62, 0.5); padding: 4px 10px; border-radius: 6px; border: 1px solid {BORDER_SUBTLE};"
        )
        right_layout.addWidget(self.wsl_badge, alignment=Qt.AlignRight)

        self.docker_badge = QLabel("Docker: Checking...")
        self.docker_badge.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; font-weight: bold; "
            f"background: rgba(35, 47, 62, 0.5); padding: 4px 10px; border-radius: 6px; border: 1px solid {BORDER_SUBTLE};"
        )
        right_layout.addWidget(self.docker_badge, alignment=Qt.AlignRight)

        layout.addLayout(right_layout)

    def update_status(self, wsl_available: bool, docker_running: bool, docker_ver: str = ""):
        if docker_running:
            self.docker_badge.setText("Docker: Running")
            self.docker_badge.setStyleSheet(
                f"color: {GREEN_BRIGHT}; font-size: 11px; font-weight: bold; "
                f"background: rgba(35, 134, 54, 0.2); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(35, 134, 54, 0.5);"
            )
        else:
            self.docker_badge.setText("Docker: Stopped")
            self.docker_badge.setStyleSheet(
                f"color: #ff7b72; font-size: 11px; font-weight: bold; "
                f"background: rgba(218, 54, 51, 0.2); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(218, 54, 51, 0.4);"
            )

        if not wsl_available:
            self.wsl_badge.setText("WSL 2: Unresponsive")
            self.wsl_badge.setStyleSheet(
                f"color: #ff7b72; font-size: 11px; font-weight: bold; "
                f"background: rgba(218, 54, 51, 0.2); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(218, 54, 51, 0.4);"
            )
        else:
            self.wsl_badge.setText(f"WSL 2: {CONFIG.wsl_distro}")
            self.wsl_badge.setStyleSheet(
                f"color: {GREEN_BRIGHT}; font-size: 11px; font-weight: 600; "
                f"background: rgba(35, 134, 54, 0.2); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(35, 134, 54, 0.5);"
            )
