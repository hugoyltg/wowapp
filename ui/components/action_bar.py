"""Action bar component containing Boot Server, Shut Off Server, and gated Enter Game hero button."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import (
    AMBER_WARNING,
    BG_CARD,
    BORDER_SUBTLE,
    GOLD_PRIMARY,
    GREEN_BRIGHT,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class ActionBar(QFrame):
    """Control center action bar."""

    start_requested = Signal()
    stop_requested = Signal()
    play_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        # Top Section: Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(14)

        # 1. Boot Server Button
        self.btn_start = QPushButton("▶  Boot Server")
        self.btn_start.setProperty("class", "PrimaryAction")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.clicked.connect(self.start_requested.emit)
        btn_layout.addWidget(self.btn_start)

        # 2. Shut Off Server Button
        self.btn_stop = QPushButton("⏹  Shut Off Server")
        self.btn_stop.setProperty("class", "DangerAction")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stop_requested.emit)
        btn_layout.addWidget(self.btn_stop)

        btn_layout.addStretch()

        # 3. Enter Game Hero Button
        self.btn_play = QPushButton("⚔  ENTER GAME (WoW 3.3.5)")
        self.btn_play.setProperty("class", "HeroEnterGame")
        self.btn_play.setCursor(Qt.PointingHandCursor)
        self.btn_play.setEnabled(False)  # Locked by default until server ready
        self.btn_play.setToolTip("Server is offline. Boot the server and wait for world initialization to play.")
        self.btn_play.clicked.connect(self.play_requested.emit)
        btn_layout.addWidget(self.btn_play)

        main_layout.addLayout(btn_layout)

        # Bottom Section: Gate Status Notice
        notice_layout = QHBoxLayout()
        notice_layout.setSpacing(8)

        self.gate_icon = QLabel("🔒")
        self.gate_icon.setStyleSheet("font-size: 13px;")
        notice_layout.addWidget(self.gate_icon)

        self.gate_label = QLabel("Enter Game is locked: Server is offline.")
        self.gate_label.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; font-weight: 500;")
        notice_layout.addWidget(self.gate_label)
        notice_layout.addStretch()

        self.feedback_label = QLabel("")
        self.feedback_label.setStyleSheet(f"font-size: 12px; color: {TEXT_SECONDARY}; font-weight: 600;")
        notice_layout.addWidget(self.feedback_label)

        main_layout.addLayout(notice_layout)

    def set_server_busy(self, is_busy: bool, action_text: str = ""):
        """Disables action buttons during an active start or stop operation."""
        self.btn_start.setEnabled(not is_busy)
        self.btn_stop.setEnabled(not is_busy)
        if is_busy:
            self.feedback_label.setText(action_text)
            self.feedback_label.setStyleSheet(f"color: {AMBER_WARNING}; font-weight: bold;")
        else:
            self.feedback_label.setText("")

    def set_readiness(self, ready: bool, reason: str = ""):
        """Updates the Enter Game hero button and safety gate label."""
        if ready:
            self.btn_play.setEnabled(True)
            self.btn_play.setToolTip("Server is fully initialized and accepting connections! Click to launch WoW.")
            self.gate_icon.setText("🟢")
            self.gate_label.setText("Server is ready! You can enter the game now.")
            self.gate_label.setStyleSheet(f"font-size: 12px; color: {GREEN_BRIGHT}; font-weight: 600;")
        else:
            self.btn_play.setEnabled(False)
            self.gate_icon.setText("🔒")
            self.gate_label.setText(f"Enter Game locked: {reason}")
            self.gate_label.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED}; font-weight: 500;")
            self.btn_play.setToolTip(f"Waiting for server readiness: {reason}")
