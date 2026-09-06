"""Log viewer component providing real-time container log monitoring."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ui.theme import FONT_MONO, TEXT_MUTED, TEXT_PRIMARY, TEXT_SECONDARY


class LogViewer(QFrame):
    """Console and log inspection widget."""

    refresh_requested = Signal(str)  # Service name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("class", "Card")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 14)
        layout.setSpacing(10)

        # Controls Bar
        top_bar = QHBoxLayout()
        top_bar.setSpacing(12)

        self.header_label = QLabel("Worldserver Live Console")
        self.header_label.setStyleSheet(
            f"font-size: 14px; font-weight: 700; color: {TEXT_PRIMARY};"
        )
        top_bar.addWidget(self.header_label)

        self.service_badge = QLabel("ac-worldserver")
        self.service_badge.setStyleSheet(
            f"background: rgba(35, 47, 62, 0.6); color: {TEXT_SECONDARY}; "
            f"font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 5px;"
        )
        top_bar.addWidget(self.service_badge)

        top_bar.addStretch()

        # Auto-refresh Toggle
        self.auto_scroll_cb = QCheckBox("Auto-Scroll")
        self.auto_scroll_cb.setChecked(True)
        top_bar.addWidget(self.auto_scroll_cb)

        # Manual Refresh Button
        self.btn_refresh = QPushButton("↻ Refresh")
        self.btn_refresh.setCursor(Qt.PointingHandCursor)
        self.btn_refresh.clicked.connect(self.request_manual_refresh)
        top_bar.addWidget(self.btn_refresh)

        # Clear Button
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setCursor(Qt.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_logs)
        top_bar.addWidget(self.btn_clear)

        layout.addLayout(top_bar)

        # Terminal Output Box
        self.terminal = QTextEdit()
        self.terminal.setProperty("class", "Terminal")
        self.terminal.setReadOnly(True)
        self.terminal.setMinimumHeight(220)
        self.terminal.setPlaceholderText("Worldserver logs will appear here once the server is started...")
        layout.addWidget(self.terminal)

    def request_manual_refresh(self):
        self.refresh_requested.emit("ac-worldserver")

    def get_selected_service(self) -> str:
        return "ac-worldserver"


    def set_logs(self, text: str):
        """Replaces the console text and optionally scrolls to bottom."""
        if self.terminal.toPlainText().strip() == text.strip():
            return  # No change

        self.terminal.setPlainText(text)
        if self.auto_scroll_cb.isChecked():
            cursor = self.terminal.textCursor()
            cursor.movePosition(QTextCursor.End)
            self.terminal.setTextCursor(cursor)

    def clear_logs(self):
        self.terminal.clear()
