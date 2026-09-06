"""Theme, color palette, and QSS styling for AzerothCore Manager."""

# Color Palette Constants
BG_MAIN = "#0b0f15"
BG_SURFACE = "#141b24"
BG_SURFACE_ALT = "#1c2532"
BG_CARD = "#17202c"
BG_CARD_HOVER = "#1f2b3b"
BG_TERMINAL = "#090d12"

BORDER_SUBTLE = "#232f3e"
BORDER_ACCENT = "#3d4f66"

TEXT_PRIMARY = "#f0f6fc"
TEXT_SECONDARY = "#9da7b3"
TEXT_MUTED = "#647080"

# Accents
GOLD_PRIMARY = "#f5ac38"
GOLD_HOVER = "#ffbe53"
GOLD_ACTIVE = "#d98f1f"
GOLD_DISABLED = "#3a2d1d"

GREEN_ONLINE = "#238636"
GREEN_HOVER = "#2ea043"
GREEN_BRIGHT = "#3fb950"

BLUE_ACCENT = "#1f6feb"
BLUE_HOVER = "#388bfd"

RED_DANGER = "#da3633"
RED_HOVER = "#f85149"

AMBER_WARNING = "#d29922"

FONT_MAIN = "'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif"
FONT_MONO = "'Consolas', 'Cascadia Code', 'JetBrains Mono', 'Courier New', monospace"


def get_stylesheet() -> str:
    """Returns the comprehensive dark QSS stylesheet for the application."""
    return f"""
    QWidget {{
        background-color: {BG_MAIN};
        color: {TEXT_PRIMARY};
        font-family: {FONT_MAIN};
        font-size: 13px;
        selection-background-color: {BLUE_ACCENT};
        selection-color: #ffffff;
    }}

    /* Main Window & Root */
    QMainWindow {{
        background-color: {BG_MAIN};
    }}

    /* Card Panels */
    QFrame.Card {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 10px;
        padding: 12px;
    }}
    QFrame.Card:hover {{
        border: 1px solid {BORDER_ACCENT};
    }}

    QFrame.HeaderCard {{
        background-color: {BG_SURFACE};
        border-bottom: 1px solid {BORDER_SUBTLE};
        padding: 16px 20px;
    }}

    /* Status Badges */
    QLabel.StatusBadge {{
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: bold;
    }}
    QLabel.StatusBadgeOnline {{
        background-color: rgba(35, 134, 54, 0.25);
        color: {GREEN_BRIGHT};
        border: 1px solid {GREEN_ONLINE};
    }}
    QLabel.StatusBadgeBooting {{
        background-color: rgba(210, 153, 34, 0.25);
        color: {AMBER_WARNING};
        border: 1px solid {AMBER_WARNING};
    }}
    QLabel.StatusBadgeStopped {{
        background-color: rgba(218, 54, 51, 0.2);
        color: #ff7b72;
        border: 1px solid rgba(218, 54, 51, 0.4);
    }}

    /* Standard Buttons */
    QPushButton {{
        background-color: {BG_SURFACE_ALT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {BG_CARD_HOVER};
        border: 1px solid {BORDER_ACCENT};
    }}
    QPushButton:pressed {{
        background-color: {BORDER_SUBTLE};
    }}
    QPushButton:disabled {{
        background-color: rgba(20, 27, 36, 0.6);
        color: {TEXT_MUTED};
        border: 1px solid rgba(35, 47, 62, 0.4);
    }}

    /* Primary Action Button (Boot Server) */
    QPushButton.PrimaryAction {{
        background-color: {GREEN_ONLINE};
        color: #ffffff;
        border: 1px solid {GREEN_BRIGHT};
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton.PrimaryAction:hover {{
        background-color: {GREEN_HOVER};
    }}
    QPushButton.PrimaryAction:pressed {{
        background-color: #1a6327;
    }}
    QPushButton.PrimaryAction:disabled {{
        background-color: #122c19;
        color: #385e42;
        border: 1px solid #1a4224;
    }}

    /* Danger Action Button (Shut Off Server) */
    QPushButton.DangerAction {{
        background-color: rgba(218, 54, 51, 0.15);
        color: #ff7b72;
        border: 1px solid rgba(218, 54, 51, 0.4);
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 13px;
        font-weight: bold;
    }}
    QPushButton.DangerAction:hover {{
        background-color: {RED_DANGER};
        color: #ffffff;
        border: 1px solid {RED_HOVER};
    }}
    QPushButton.DangerAction:pressed {{
        background-color: #a02220;
    }}
    QPushButton.DangerAction:disabled {{
        background-color: transparent;
        color: {TEXT_MUTED};
        border: 1px solid rgba(40, 50, 65, 0.4);
    }}

    /* Hero "ENTER GAME" Button */
    QPushButton.HeroEnterGame {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d98f1f, stop:1 {GOLD_PRIMARY});
        color: #0b0f15;
        border: 1px solid {GOLD_HOVER};
        border-radius: 10px;
        padding: 14px 28px;
        font-size: 15px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }}
    QPushButton.HeroEnterGame:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {GOLD_PRIMARY}, stop:1 {GOLD_HOVER});
        color: #000000;
    }}
    QPushButton.HeroEnterGame:pressed {{
        background-color: {GOLD_ACTIVE};
    }}
    QPushButton.HeroEnterGame:disabled {{
        background: {GOLD_DISABLED};
        color: #7a6042;
        border: 1px solid #4a3821;
    }}

    /* Terminal / Log Viewer */
    QTextEdit.Terminal {{
        background-color: {BG_TERMINAL};
        color: #a9b7c6;
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        font-family: {FONT_MONO};
        font-size: 12px;
        line-height: 1.4;
        padding: 8px;
    }}

    /* Combo Box */
    QComboBox {{
        background-color: {BG_SURFACE_ALT};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        padding: 5px 12px;
        font-weight: 500;
    }}
    QComboBox:hover {{
        border: 1px solid {BORDER_ACCENT};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid {BORDER_SUBTLE};
    }}
    QComboBox QAbstractItemView {{
        background-color: {BG_SURFACE};
        border: 1px solid {BORDER_ACCENT};
        color: {TEXT_PRIMARY};
        selection-background-color: {BLUE_ACCENT};
    }}

    /* Scrollbars */
    QScrollBar:vertical {{
        background: {BG_TERMINAL};
        width: 10px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER_ACCENT};
        min-height: 25px;
        border-radius: 5px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {TEXT_MUTED};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    /* CheckBox */
    QCheckBox {{
        color: {TEXT_SECONDARY};
        spacing: 6px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {BORDER_ACCENT};
        background: {BG_SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {BLUE_ACCENT};
        border-color: {BLUE_HOVER};
    }}

    /* Tooltips */
    QToolTip {{
        background-color: {BG_SURFACE};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_ACCENT};
        padding: 6px 10px;
        border-radius: 6px;
    }}

    /* Sidebar Navigation */
    QFrame#Sidebar {{
        background-color: {BG_SURFACE};
        border-right: 1px solid {BORDER_SUBTLE};
        min-width: 210px;
        max-width: 210px;
    }}

    QPushButton.NavButton {{
        background-color: transparent;
        color: {TEXT_SECONDARY};
        border: none;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: left;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton.NavButton:hover {{
        background-color: {BG_SURFACE_ALT};
        color: {TEXT_PRIMARY};
    }}
    QPushButton.NavButton:checked {{
        background-color: rgba(245, 172, 56, 0.12);
        color: {GOLD_PRIMARY};
        border-left: 3px solid {GOLD_PRIMARY};
        font-weight: bold;
    }}

    /* Category Pill Selector */
    QPushButton.CategoryPill {{
        background-color: {BG_SURFACE};
        color: {TEXT_SECONDARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 20px;
        padding: 8px 18px;
        font-weight: 600;
    }}
    QPushButton.CategoryPill:hover {{
        background-color: {BG_SURFACE_ALT};
        color: {TEXT_PRIMARY};
        border-color: {BORDER_ACCENT};
    }}
    QPushButton.CategoryPill:checked {{
        background-color: {GOLD_PRIMARY};
        color: #0b0f15;
        border: 1px solid {GOLD_HOVER};
        font-weight: bold;
    }}

    /* Input Fields */
    QLineEdit {{
        background-color: {BG_SURFACE};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}
    QLineEdit:focus {{
        border: 1px solid {BLUE_HOVER};
        background-color: {BG_TERMINAL};
    }}

    /* SpinBoxes */
    QSpinBox, QDoubleSpinBox {{
        background-color: {BG_SURFACE};
        color: {TEXT_PRIMARY};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        padding: 5px 8px;
        font-weight: 600;
        font-size: 13px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {GOLD_PRIMARY};
    }}
    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background-color: {BG_SURFACE_ALT};
        width: 16px;
        border: none;
    }}
    QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
    QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
        background-color: {BORDER_ACCENT};
    }}

    /* Sliders */
    QSlider::groove:horizontal {{
        border: none;
        height: 6px;
        background: {BORDER_SUBTLE};
        border-radius: 3px;
    }}
    QSlider::sub-page:horizontal {{
        background: {GOLD_PRIMARY};
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: #ffffff;
        border: 2px solid {GOLD_PRIMARY};
        width: 16px;
        margin-top: -5px;
        margin-bottom: -5px;
        border-radius: 8px;
    }}
    QSlider::handle:horizontal:hover {{
        background: {GOLD_HOVER};
    }}

    /* Table Grid (Database Explorer) */
    QTableView, QTableWidget {{
        background-color: {BG_TERMINAL};
        color: {TEXT_PRIMARY};
        gridline-color: {BORDER_SUBTLE};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 8px;
        selection-background-color: rgba(31, 111, 235, 0.35);
        selection-color: #ffffff;
        font-family: {FONT_MONO};
        font-size: 12px;
    }}
    QTableView::item {{
        padding: 5px 8px;
    }}
    QTableView::item:selected {{
        background-color: rgba(31, 111, 235, 0.4);
    }}
    QHeaderView::section {{
        background-color: {BG_SURFACE};
        color: {TEXT_SECONDARY};
        font-family: {FONT_MAIN};
        font-weight: 700;
        font-size: 12px;
        border: none;
        border-bottom: 1px solid {BORDER_SUBTLE};
        border-right: 1px solid {BORDER_SUBTLE};
        padding: 6px 10px;
    }}
    QHeaderView::section:hover {{
        background-color: {BG_SURFACE_ALT};
        color: {TEXT_PRIMARY};
    }}

    /* List Views */
    QListWidget {{
        background-color: {BG_SURFACE};
        border: 1px solid {BORDER_SUBTLE};
        border-radius: 6px;
        padding: 4px;
        color: {TEXT_PRIMARY};
    }}
    QListWidget::item {{
        padding: 6px 10px;
        border-radius: 4px;
    }}
    QListWidget::item:hover {{
        background-color: {BG_SURFACE_ALT};
    }}
    QListWidget::item:selected {{
        background-color: rgba(245, 172, 56, 0.2);
        color: {GOLD_PRIMARY};
        font-weight: bold;
    }}
    """
