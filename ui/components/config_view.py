"""Curated Game Configuration View for AzerothCore."""

from typing import Any, Dict, List

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.accounts import create_account, list_accounts_from_db, set_gm_level
from app.game_config import CONFIG_MGR, CURATED_SETTINGS, ConfigOptionDef
from ui.theme import (
    AMBER_WARNING,
    BG_CARD,
    BG_CARD_HOVER,
    BG_SURFACE,
    BG_SURFACE_ALT,
    BG_TERMINAL,
    BORDER_ACCENT,
    BORDER_SUBTLE,
    GOLD_HOVER,
    GOLD_PRIMARY,
    GREEN_BRIGHT,
    GREEN_ONLINE,
    RED_DANGER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class ConfigView(QWidget):
    """Configuration management view with categorized sections and interactive controls."""

    settings_saved = Signal(str)

    CATEGORIES = [
        ("playerbots", "⚔ Playerbots", "Manage bot population, levels, DK restrictions, and AI behavior"),
        ("world", "🌍 World Rates", "Tune XP multipliers, gold drop rates, loot quality, and PvP rates"),
        ("progression", "🧙 Progression", "Control expansion stages, raid/dungeon access, and race unlock rules"),
        ("server", "🛠 Server", "Configure network ports, player caps, and console logging verbosity"),
        ("accounts", "👤 Accounts", "Create accounts and assign GM security levels"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_category = "playerbots"
        self._controls: Dict[str, QWidget] = {}
        self._current_values: Dict[str, Any] = {}
        self._is_dirty = False

        self.init_ui()
        self.load_values()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(18, 14, 18, 14)
        root_layout.setSpacing(12)

        # 1. Top Header & Action Controls
        header_layout = QHBoxLayout()

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        main_title = QLabel("AzerothCore Configuration Center")
        main_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {TEXT_PRIMARY};")
        self.sub_title = QLabel("Select a category to customize game rules and server options.")
        self.sub_title.setStyleSheet(f"font-size: 12px; color: {TEXT_MUTED};")
        title_col.addWidget(main_title)
        title_col.addWidget(self.sub_title)
        header_layout.addLayout(title_col)

        header_layout.addStretch()

        # Reload Button
        self.btn_reload = QPushButton("🔄 Reload")
        self.btn_reload.setCursor(Qt.PointingHandCursor)
        self.btn_reload.setToolTip("Discard unsaved changes and reload config files from disk.")
        self.btn_reload.clicked.connect(self.load_values)
        header_layout.addWidget(self.btn_reload)

        # Save Button
        self.btn_save = QPushButton("💾 Save Changes")
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet(
            f"background-color: {GOLD_PRIMARY}; color: #0b0f15; font-weight: bold; border-radius: 6px; padding: 8px 18px;"
        )
        self.btn_save.clicked.connect(self.on_save_clicked)
        header_layout.addWidget(self.btn_save)

        root_layout.addLayout(header_layout)

        # 2. Category Pill Selector
        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(10)
        self.pill_group = QButtonGroup(self)
        self.pill_group.setExclusive(True)

        for idx, (cat_key, cat_label, _) in enumerate(self.CATEGORIES):
            pill = QPushButton(cat_label)
            pill.setProperty("class", "CategoryPill")
            pill.setCheckable(True)
            pill.setCursor(Qt.PointingHandCursor)
            self.pill_group.addButton(pill, idx)
            pills_layout.addWidget(pill)
            if idx == 0:
                pill.setChecked(True)

        self.pill_group.idClicked.connect(self._on_category_changed)
        pills_layout.addStretch()
        root_layout.addLayout(pills_layout)

        # 3. Scrollable Settings Form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        self.form_container = QWidget()
        self.form_layout = QVBoxLayout(self.form_container)
        self.form_layout.setContentsMargins(4, 8, 4, 8)
        self.form_layout.setSpacing(10)

        scroll.setWidget(self.form_container)
        root_layout.addWidget(scroll)

        # 4. Status banner
        self.status_banner = QLabel("Ready. Modify settings and click Save to apply.")
        self.status_banner.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; padding: 4px;")
        root_layout.addWidget(self.status_banner)

        # Render initial form
        self.render_category("playerbots")

    def _on_category_changed(self, idx: int):
        cat_key = self.CATEGORIES[idx][0]
        self._current_category = cat_key
        desc = self.CATEGORIES[idx][2]
        self.sub_title.setText(desc)
        self.render_category(cat_key)

    def render_category(self, category: str):
        """Clears and rebuilds the setting cards for the selected category."""
        # Clear existing layout
        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._controls.clear()

        if category == "accounts":
            acct_widget = self._create_account_manager_widget()
            self.form_layout.addWidget(acct_widget)
            self.form_layout.addStretch()
            return

        # Find settings belonging to this category
        cat_settings = [s for s in CURATED_SETTINGS if s.category == category]

        for opt in cat_settings:
            card = self._create_option_card(opt)
            self.form_layout.addWidget(card)

        self.form_layout.addStretch()

    def _create_option_card(self, opt: ConfigOptionDef) -> QFrame:
        card = QFrame()
        card.setProperty("class", "Card")
        card.setStyleSheet(
            f"background-color: {BG_CARD}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px; padding: 12px;"
        )

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(14)

        # Info side (Label, Key, Description)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)

        lbl_title = QLabel(opt.label)
        lbl_title.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {TEXT_PRIMARY};")
        title_row.addWidget(lbl_title)

        key_badge = QLabel(f"[{opt.key}]")
        key_badge.setStyleSheet(f"font-size: 11px; font-family: monospace; color: {TEXT_MUTED};")
        title_row.addWidget(key_badge)
        title_row.addStretch()

        info_layout.addLayout(title_row)

        lbl_desc = QLabel(opt.description)
        lbl_desc.setStyleSheet(f"font-size: 11px; color: {TEXT_SECONDARY};")
        lbl_desc.setWordWrap(True)
        info_layout.addWidget(lbl_desc)

        card_layout.addLayout(info_layout, stretch=3)

        # Control side
        control_box = self._build_control_widget(opt)
        card_layout.addWidget(control_box, stretch=2, alignment=Qt.AlignRight | Qt.AlignVCenter)

        return card

    def _build_control_widget(self, opt: ConfigOptionDef) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        current_val = self._current_values.get(opt.key, opt.default)

        if opt.choices:
            # Dropdown ComboBox
            combo = QComboBox()
            combo.setMinimumWidth(280)
            for val, text in opt.choices.items():
                combo.addItem(text, val)
            # Find and set current
            idx = combo.findData(current_val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(lambda: self._mark_dirty())
            self._controls[opt.key] = combo
            layout.addWidget(combo)

        elif opt.val_type is bool:
            # Checkbox Toggle
            chk = QCheckBox("Enabled" if current_val else "Disabled")
            chk.setChecked(bool(current_val))
            chk.toggled.connect(lambda checked, c=chk: self._on_checkbox_toggled(c, checked))
            self._controls[opt.key] = chk
            layout.addWidget(chk)

        elif opt.val_type is int and opt.min_val is not None and opt.max_val is not None:
            # Spinbox + Slider for int
            spin = QSpinBox()
            spin.setRange(int(opt.min_val), int(opt.max_val))
            spin.setSingleStep(int(opt.step or 1))
            spin.setValue(int(current_val))
            if opt.unit:
                spin.setSuffix(f" {opt.unit}")

            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(opt.min_val), int(opt.max_val))
            slider.setSingleStep(int(opt.step or 1))
            slider.setValue(int(current_val))
            slider.setMinimumWidth(120)

            # Sync slider & spinbox
            spin.valueChanged.connect(slider.setValue)
            slider.valueChanged.connect(spin.setValue)
            spin.valueChanged.connect(lambda: self._mark_dirty())

            self._controls[opt.key] = spin
            layout.addWidget(slider)
            layout.addWidget(spin)

        elif opt.val_type is float and opt.min_val is not None and opt.max_val is not None:
            # DoubleSpinBox for floats (e.g. rates)
            dspin = QDoubleSpinBox()
            dspin.setRange(float(opt.min_val), float(opt.max_val))
            dspin.setSingleStep(float(opt.step or 0.5))
            dspin.setDecimals(2)
            dspin.setValue(float(current_val))
            if opt.unit:
                dspin.setSuffix(f" {opt.unit}")

            # Scale slider 10x
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(opt.min_val * 10), int(opt.max_val * 10))
            slider.setValue(int(current_val * 10))
            slider.setMinimumWidth(120)

            dspin.valueChanged.connect(lambda v: slider.setValue(int(v * 10)))
            slider.valueChanged.connect(lambda v: dspin.setValue(v / 10.0))
            dspin.valueChanged.connect(lambda: self._mark_dirty())

            self._controls[opt.key] = dspin
            layout.addWidget(slider)
            layout.addWidget(dspin)

        return container

    def _on_checkbox_toggled(self, chk: QCheckBox, checked: bool):
        chk.setText("Enabled" if checked else "Disabled")
        self._mark_dirty()

    # ------------------------------------------------------------------
    # Account Manager Widget
    # ------------------------------------------------------------------

    def _create_account_manager_widget(self) -> QWidget:
        """Builds the account creation form and account list panel."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        # --- Create Account Card ---
        create_card = QFrame()
        create_card.setStyleSheet(
            f"background-color: {BG_CARD}; border: 1px solid {BORDER_ACCENT}; "
            f"border-radius: 10px; padding: 16px;"
        )
        create_layout = QVBoxLayout(create_card)
        create_layout.setSpacing(12)

        title = QLabel("➕ Create New Account")
        title.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {TEXT_PRIMARY};")
        create_layout.addWidget(title)

        desc = QLabel(
            "Creates an AzerothCore login account. "
            "<b>Requires the worldserver container to be running.</b>"
        )
        desc.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        desc.setWordWrap(True)
        create_layout.addWidget(desc)

        # Form fields
        fields_layout = QHBoxLayout()
        fields_layout.setSpacing(10)

        self._acct_username = QLineEdit()
        self._acct_username.setPlaceholderText("Username")
        self._acct_username.setMinimumWidth(160)
        fields_layout.addWidget(self._acct_username)

        self._acct_password = QLineEdit()
        self._acct_password.setPlaceholderText("Password")
        self._acct_password.setEchoMode(QLineEdit.Password)
        self._acct_password.setMinimumWidth(160)
        fields_layout.addWidget(self._acct_password)

        gm_label = QLabel("GM Level:")
        gm_label.setStyleSheet(f"color: {TEXT_SECONDARY}; font-weight: 600;")
        fields_layout.addWidget(gm_label)

        self._acct_gm_level = QComboBox()
        self._acct_gm_level.addItem("0 — Player", 0)
        self._acct_gm_level.addItem("1 — Moderator", 1)
        self._acct_gm_level.addItem("2 — GameMaster", 2)
        self._acct_gm_level.addItem("3 — Administrator", 3)
        self._acct_gm_level.setCurrentIndex(3)  # default to GM3
        self._acct_gm_level.setMinimumWidth(180)
        fields_layout.addWidget(self._acct_gm_level)

        fields_layout.addStretch()
        create_layout.addLayout(fields_layout)

        # Action buttons row
        btn_row = QHBoxLayout()
        btn_create = QPushButton("✚ Create Account")
        btn_create.setCursor(Qt.PointingHandCursor)
        btn_create.setStyleSheet(
            f"background-color: {GOLD_PRIMARY}; color: #0b0f15; font-weight: bold; "
            f"border-radius: 6px; padding: 8px 20px;"
        )
        btn_create.clicked.connect(self._on_create_account)
        btn_row.addWidget(btn_create)
        btn_row.addStretch()
        create_layout.addLayout(btn_row)

        # Result banner
        self._acct_result = QLabel("")
        self._acct_result.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED}; padding: 2px;")
        self._acct_result.setWordWrap(True)
        create_layout.addWidget(self._acct_result)

        layout.addWidget(create_card)

        # --- Existing Accounts Card ---
        list_card = QFrame()
        list_card.setStyleSheet(
            f"background-color: {BG_CARD}; border: 1px solid {BORDER_SUBTLE}; "
            f"border-radius: 10px; padding: 16px;"
        )
        list_layout = QVBoxLayout(list_card)
        list_layout.setSpacing(8)

        list_header = QHBoxLayout()
        list_title = QLabel("📋 Existing Accounts")
        list_title.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {TEXT_PRIMARY};")
        list_header.addWidget(list_title)
        list_header.addStretch()
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.clicked.connect(self._refresh_accounts_table)
        list_header.addWidget(btn_refresh)
        list_layout.addLayout(list_header)

        self._acct_table = QTableWidget()
        self._acct_table.setColumnCount(4)
        self._acct_table.setHorizontalHeaderLabels(["ID", "Username", "Email", "Joined"])
        self._acct_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._acct_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._acct_table.setMinimumHeight(200)
        list_layout.addWidget(self._acct_table)

        self._acct_list_status = QLabel("Click Refresh to load accounts (requires server running).")
        self._acct_list_status.setStyleSheet(f"font-size: 11px; color: {TEXT_MUTED};")
        list_layout.addWidget(self._acct_list_status)

        layout.addWidget(list_card)

        # Auto-load accounts on tab open
        self._refresh_accounts_table()

        return container

    def _on_create_account(self):
        """Handles Create Account button click."""
        username = self._acct_username.text().strip()
        password = self._acct_password.text().strip()
        gm_level = self._acct_gm_level.currentData()

        ok, msg = create_account(username, password)
        if not ok:
            self._acct_result.setText(f"✗ {msg}")
            self._acct_result.setStyleSheet(f"font-size: 11px; color: #ff7b72; font-weight: bold;")
            return

        # Set GM level
        gm_ok, gm_msg = set_gm_level(username, gm_level)

        level_names = {0: "Player", 1: "Moderator", 2: "GameMaster", 3: "Administrator"}
        result_text = (
            f"✓ Account '{username}' created · "
            f"GM Level {gm_level} ({level_names[gm_level]}) applied."
        )
        self._acct_result.setText(result_text)
        self._acct_result.setStyleSheet(
            f"font-size: 11px; color: {GREEN_BRIGHT}; font-weight: bold;"
        )
        self._acct_username.clear()
        self._acct_password.clear()
        self._refresh_accounts_table()

    def _refresh_accounts_table(self):
        """Loads accounts from the DB and populates the table."""
        if not hasattr(self, "_acct_table"):
            return
        ok, msg, accounts = list_accounts_from_db()
        self._acct_table.setRowCount(0)
        if not ok:
            self._acct_list_status.setText(f"⚠ {msg}")
            self._acct_list_status.setStyleSheet(f"font-size: 11px; color: {AMBER_WARNING};")
            return

        self._acct_table.setRowCount(len(accounts))
        for r, acct in enumerate(accounts):
            self._acct_table.setItem(r, 0, QTableWidgetItem(str(acct["id"])))
            self._acct_table.setItem(r, 1, QTableWidgetItem(acct["username"]))
            self._acct_table.setItem(r, 2, QTableWidgetItem(acct["email"]))
            self._acct_table.setItem(r, 3, QTableWidgetItem(acct["joindate"]))

        self._acct_list_status.setText(f"{len(accounts)} account(s) loaded from acore_auth.")
        self._acct_list_status.setStyleSheet(f"font-size: 11px; color: {GREEN_BRIGHT};")

    def _mark_dirty(self):
        self._is_dirty = True
        self.btn_save.setText("💾 Save Changes *")
        self.status_banner.setText("● Unsaved changes pending. Click 'Save Changes' to apply.")
        self.status_banner.setStyleSheet(f"color: {AMBER_WARNING}; font-size: 11px; padding: 4px; font-weight: bold;")

    def load_values(self):
        """Fetches live configuration values from file system."""
        self._current_values = CONFIG_MGR.get_all_curated_values()
        self.render_category(self._current_category)
        self._is_dirty = False
        self.btn_save.setText("💾 Save Changes")
        self.status_banner.setText("Configuration successfully synchronized with server files.")
        self.status_banner.setStyleSheet(f"color: {GREEN_BRIGHT}; font-size: 11px; padding: 4px;")

    def on_save_clicked(self):
        """Collects updated values and writes to config files."""
        updates: Dict[str, Any] = {}

        # Collect current visible widget values
        for key, widget in self._controls.items():
            if isinstance(widget, QCheckBox):
                updates[key] = widget.isChecked()
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                updates[key] = widget.value()
            elif isinstance(widget, QComboBox):
                updates[key] = widget.currentData()

        # Merge with previously loaded values
        self._current_values.update(updates)

        # Save to disk
        success, msg = CONFIG_MGR.save_settings(self._current_values)
        if success:
            self._is_dirty = False
            self.btn_save.setText("💾 Save Changes")
            self.status_banner.setText(f"✓ {msg}. Timestamped backups created in .backups.")
            self.status_banner.setStyleSheet(f"color: {GREEN_BRIGHT}; font-size: 11px; padding: 4px; font-weight: bold;")
            self.settings_saved.emit(msg)
            QMessageBox.information(
                self,
                "Settings Saved",
                f"{msg}\n\n"
                "Automatic backups were saved in .backups.\n"
                "Note: Restart server or use in-game '.reload config' to apply new values."
            )
        else:
            self.status_banner.setText(f"✗ Failed to save: {msg}")
            self.status_banner.setStyleSheet(f"color: #ff7b72; font-size: 11px; padding: 4px;")
            QMessageBox.warning(self, "Save Error", f"Could not save settings:\n{msg}")
