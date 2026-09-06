"""Left Navigation Sidebar for AzerothCore Manager."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.theme import (
    BORDER_SUBTLE,
    GOLD_PRIMARY,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class Sidebar(QFrame):
    """Vertical navigation sidebar with category selector and status indicator."""

    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        self.nav_buttons = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 18, 12, 18)
        layout.setSpacing(8)

        # 1. App Branding / Logo
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)

        title_label = QLabel("⚔ AZEROTHCORE")
        title_label.setStyleSheet(
            f"font-size: 14px; font-weight: 900; letter-spacing: 1px; color: {GOLD_PRIMARY};"
        )
        subtitle_label = QLabel("WotLK 3.3.5a Manager")
        subtitle_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {TEXT_MUTED}; text-transform: uppercase;"
        )
        brand_layout.addWidget(title_label)
        brand_layout.addWidget(subtitle_label)

        layout.addLayout(brand_layout)
        layout.addSpacing(18)

        # Section Label
        nav_label = QLabel("NAVIGATION")
        nav_label.setStyleSheet(
            f"font-size: 10px; font-weight: 700; letter-spacing: 1.2px; color: {TEXT_MUTED}; padding-left: 6px;"
        )
        layout.addWidget(nav_label)
        layout.addSpacing(4)

        # 2. Navigation Items
        # (index, icon, title, subtitle)
        items = [
            (0, "🖥️", "Server", "Containers & Launch"),
            (1, "⚙️", "Game Config", "Bots, Rates & Progression"),
            (2, "🗄️", "Database", "Find, Replace & Save"),
            (3, "💻", "Terminal", "WSL Interactive Shell"),
        ]

        for idx, icon, title, subtitle in items:
            btn = self._create_nav_button(idx, icon, title, subtitle)
            self.button_group.addButton(btn, idx)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        self.button_group.idClicked.connect(self._on_item_clicked)

        # Set first item active
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)

        layout.addStretch()

        # 3. Footer info
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(3)
        footer_layout.setContentsMargins(6, 0, 6, 0)

        patch_lbl = QLabel("Client: 3.3.5a (12340)")
        patch_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        engine_lbl = QLabel("AzerothCore v2026")
        engine_lbl.setStyleSheet(f"font-size: 10px; color: {TEXT_MUTED};")

        footer_layout.addWidget(patch_lbl)
        footer_layout.addWidget(engine_lbl)
        layout.addLayout(footer_layout)

    def _create_nav_button(self, idx: int, icon: str, title: str, subtitle: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("class", "NavButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)

        btn_layout = QHBoxLayout(btn)
        btn_layout.setContentsMargins(10, 8, 10, 8)
        btn_layout.setSpacing(10)

        # Icon
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 18px; background: transparent;")
        btn_layout.addWidget(icon_lbl)

        # Text column
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: inherit; background: transparent;")
        subtitle_lbl = QLabel(subtitle)
        subtitle_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; background: transparent;")

        text_layout.addWidget(title_lbl)
        text_layout.addWidget(subtitle_lbl)

        btn_layout.addLayout(text_layout)
        btn_layout.addStretch()

        return btn

    def _on_item_clicked(self, idx: int):
        self.page_changed.emit(idx)

    def select_page(self, index: int):
        """Programmatically activate a tab by index."""
        btn = self.button_group.button(index)
        if btn:
            btn.setChecked(True)
            self.page_changed.emit(index)
