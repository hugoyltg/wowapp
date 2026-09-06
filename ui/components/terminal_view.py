"""Interactive WSL Terminal Panel for AzerothCore Manager.

Spawns a persistent bash shell inside WSL via QProcess, pre-cd'd to the
AzerothCore project directory. Streams stdout/stderr live and accepts
stdin input from the user.
"""

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.config import CONFIG
from ui.theme import (
    AMBER_WARNING,
    BG_CARD,
    BG_TERMINAL,
    BORDER_ACCENT,
    BORDER_SUBTLE,
    FONT_MONO,
    GOLD_PRIMARY,
    GREEN_BRIGHT,
    GREEN_ONLINE,
    RED_DANGER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class TerminalView(QWidget):
    """Interactive WSL bash terminal panel with live output streaming."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._history: list[str] = []
        self._history_idx: int = -1
        self.init_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(10)

        # Header
        header = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        main_title = QLabel("💻 WSL Interactive Terminal")
        main_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {TEXT_PRIMARY};")
        sub_title = QLabel(
            f"Persistent bash shell · {CONFIG.wsl_distro} · {CONFIG.acore_path}"
        )
        sub_title.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        title_col.addWidget(main_title)
        title_col.addWidget(sub_title)
        header.addLayout(title_col)
        header.addStretch()

        # Status indicator
        self.status_pill = QLabel("● Stopped")
        self.status_pill.setStyleSheet(
            f"padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; "
            f"background-color: rgba(218, 54, 51, 0.2); color: #ff7b72; "
            f"border: 1px solid rgba(218, 54, 51, 0.4);"
        )
        header.addWidget(self.status_pill)

        # Restart button
        self.btn_restart = QPushButton("🔄 Restart Shell")
        self.btn_restart.setCursor(Qt.PointingHandCursor)
        self.btn_restart.setToolTip("Kill the current shell and spawn a fresh one.")
        self.btn_restart.clicked.connect(self.start_shell)
        header.addWidget(self.btn_restart)

        # Clear button
        btn_clear = QPushButton("🗑 Clear")
        btn_clear.setCursor(Qt.PointingHandCursor)
        btn_clear.clicked.connect(self._clear_output)
        header.addWidget(btn_clear)

        root_layout.addLayout(header)

        # Output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setProperty("class", "Terminal")
        self.output.setStyleSheet(
            f"background-color: {BG_TERMINAL}; color: #a9b7c6; "
            f"border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; "
            f"font-family: {FONT_MONO}; font-size: 12px; padding: 10px;"
        )
        self.output.setMinimumHeight(200)
        root_layout.addWidget(self.output, stretch=1)

        # Input bar
        input_frame = QFrame()
        input_frame.setStyleSheet(
            f"background-color: {BG_CARD}; border: 1px solid {BORDER_ACCENT}; "
            f"border-radius: 8px; padding: 4px;"
        )
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 6, 6, 6)
        input_layout.setSpacing(8)

        prompt_lbl = QLabel("$")
        prompt_lbl.setStyleSheet(
            f"font-family: {FONT_MONO}; font-size: 14px; font-weight: bold; color: {GOLD_PRIMARY};"
        )
        input_layout.addWidget(prompt_lbl)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Enter command... (↑↓ for history, Enter to send)")
        self.input_line.setStyleSheet(
            f"background: transparent; border: none; color: {TEXT_PRIMARY}; "
            f"font-family: {FONT_MONO}; font-size: 13px;"
        )
        self.input_line.returnPressed.connect(self._send_input)
        self.input_line.installEventFilter(self)
        input_layout.addWidget(self.input_line, stretch=1)

        self.btn_send = QPushButton("Send ↵")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.setStyleSheet(
            f"background-color: {GREEN_ONLINE}; color: #ffffff; font-weight: bold; "
            f"border-radius: 6px; padding: 6px 14px;"
        )
        self.btn_send.clicked.connect(self._send_input)
        input_layout.addWidget(self.btn_send)

        root_layout.addWidget(input_frame)

        # Hint bar
        hint = QLabel(
            "💡 Tip: Use <b>.account create &lt;user&gt; &lt;pass&gt;</b> and "
            "<b>.account set gmlevel &lt;user&gt; &lt;level&gt; -1</b> to manage accounts in-game. "
            "Or run any Linux / docker command directly."
        )
        hint.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        hint.setWordWrap(True)
        root_layout.addWidget(hint)

    # ------------------------------------------------------------------
    # Process Management
    # ------------------------------------------------------------------

    def start_shell(self):
        """Spawns (or restarts) the WSL bash shell process."""
        self.stop_shell()

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_output)
        self._process.finished.connect(self._on_process_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        # Launch WSL bash, cd to acore path immediately
        args = [
            "-d", CONFIG.wsl_distro,
            "--",
            "bash", "--login", "-i",
        ]
        self._process.start("wsl", args)

        if self._process.waitForStarted(5000):
            self._set_status_running()
            self._append_system(
                f"Shell started · {CONFIG.wsl_distro} · cd {CONFIG.acore_path}"
            )
            # CD to the acore project dir immediately
            self._write_line(f"cd {CONFIG.acore_path}")
            self._write_line("echo '--- Ready ---'")
        else:
            self._set_status_stopped()
            self._append_system("Failed to start WSL shell. Is WSL installed and configured?", error=True)

    def stop_shell(self):
        """Terminates the running shell process cleanly."""
        if self._process and self._process.state() != QProcess.NotRunning:
            self._write_line("exit")
            if not self._process.waitForFinished(2000):
                self._process.kill()
            self._process = None
        self._set_status_stopped()

    def ensure_running(self):
        """Starts the shell if it isn't already running. Called when tab is activated."""
        if self._process is None or self._process.state() == QProcess.NotRunning:
            self.start_shell()

    # ------------------------------------------------------------------
    # I/O
    # ------------------------------------------------------------------

    def _write_line(self, text: str):
        """Sends a line of text to the process stdin."""
        if self._process and self._process.state() == QProcess.Running:
            self._process.write((text + "\n").encode("utf-8"))

    def _send_input(self):
        """Reads the input field and sends it to the shell."""
        text = self.input_line.text()
        if not text.strip():
            return

        # Save to history
        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._history_idx = len(self._history)

        # Echo the command in gold
        self._append_html(
            f'<span style="color:{GOLD_PRIMARY}; font-weight:bold;">$ {self._escape(text)}</span><br>'
        )

        if self._process and self._process.state() == QProcess.Running:
            self._write_line(text)
        else:
            self._append_system("Shell is not running. Click 'Restart Shell'.", error=True)

        self.input_line.clear()

    def _on_output(self):
        """Reads available stdout/stderr from the process and appends to display."""
        if not self._process:
            return
        raw = bytes(self._process.readAllStandardOutput())
        try:
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = str(raw)

        for line in text.splitlines():
            if line.strip() == "--- Ready ---":
                continue  # swallow our own sentinel
            self._append_output(line)

    def _on_process_finished(self, exit_code: int, exit_status):
        self._set_status_stopped()
        self._append_system(f"Shell exited (code {exit_code}).")

    def _on_process_error(self, error):
        self._set_status_stopped()
        self._append_system(f"Process error: {error}", error=True)

    # ------------------------------------------------------------------
    # History navigation via eventFilter
    # ------------------------------------------------------------------

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import Qt as _Qt

        if obj is self.input_line and event.type() == QEvent.KeyPress:
            key = event.key()
            if key == _Qt.Key_Up:
                if self._history and self._history_idx > 0:
                    self._history_idx -= 1
                    self.input_line.setText(self._history[self._history_idx])
                return True
            if key == _Qt.Key_Down:
                if self._history_idx < len(self._history) - 1:
                    self._history_idx += 1
                    self.input_line.setText(self._history[self._history_idx])
                else:
                    self._history_idx = len(self._history)
                    self.input_line.clear()
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _append_output(self, line: str):
        """Appends a plain output line, coloring prompt/error lines automatically."""
        escaped = self._escape(line)
        if any(kw in line.lower() for kw in ("error", "failed", "not found", "denied")):
            color = "#ff7b72"
        elif any(kw in line.lower() for kw in ("warning", "warn")):
            color = AMBER_WARNING
        elif line.strip().startswith("$") or "@" in line:
            color = GREEN_BRIGHT
        else:
            color = "#a9b7c6"
        self._append_html(f'<span style="color:{color};">{escaped}</span><br>')

    def _append_system(self, msg: str, error: bool = False):
        color = "#ff7b72" if error else TEXT_MUTED
        self._append_html(
            f'<span style="color:{color}; font-style:italic;">▶ {self._escape(msg)}</span><br>'
        )

    def _append_html(self, html: str):
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertHtml(html)
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def _clear_output(self):
        self.output.clear()

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ------------------------------------------------------------------
    # Status pill
    # ------------------------------------------------------------------

    def _set_status_running(self):
        self.status_pill.setText("● Shell Running")
        self.status_pill.setStyleSheet(
            f"padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; "
            f"background-color: rgba(35, 134, 54, 0.25); color: {GREEN_BRIGHT}; "
            f"border: 1px solid {GREEN_ONLINE};"
        )
        self.input_line.setEnabled(True)
        self.btn_send.setEnabled(True)

    def _set_status_stopped(self):
        self.status_pill.setText("● Stopped")
        self.status_pill.setStyleSheet(
            f"padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; "
            f"background-color: rgba(218, 54, 51, 0.2); color: #ff7b72; "
            f"border: 1px solid rgba(218, 54, 51, 0.4);"
        )
        self.input_line.setEnabled(False)
        self.btn_send.setEnabled(False)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        self.stop_shell()
        super().closeEvent(event)
