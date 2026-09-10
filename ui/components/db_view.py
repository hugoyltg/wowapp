"""Live Database Explorer & Editor for AzerothCore."""

import time
from typing import Any, Dict, List, Optional, Set, Tuple

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.database import DB_MGR
from ui.theme import (
    AMBER_WARNING,
    BG_CARD,
    BG_SURFACE,
    BG_SURFACE_ALT,
    BG_TERMINAL,
    BLUE_ACCENT,
    BORDER_ACCENT,
    BORDER_SUBTLE,
    GOLD_PRIMARY,
    GREEN_BRIGHT,
    GREEN_ONLINE,
    RED_DANGER,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


class DbQueryWorker(QThread):
    """Background worker for querying data without blocking the UI thread."""

    data_ready = Signal(list, list, int, float, str)  # cols, rows, total_cnt, elapsed, error

    def __init__(
        self,
        db_name: str,
        table_name: str,
        search_query: str,
        search_column: str,
        where_clause: str,
        limit: int,
        offset: int,
        sort_column: str = "",
        sort_order: str = "ASC",
        parent=None,
    ):
        super().__init__(parent)
        self.db_name = db_name
        self.table_name = table_name
        self.search_query = search_query
        self.search_column = search_column
        self.where_clause = where_clause
        self.limit = limit
        self.offset = offset
        self.sort_column = sort_column
        self.sort_order = sort_order

    def run(self):
        t0 = time.time()
        try:
            cols, rows, total = DB_MGR.query_table(
                db_name=self.db_name,
                table_name=self.table_name,
                search_query=self.search_query,
                search_column=self.search_column,
                where_clause=self.where_clause,
                limit=self.limit,
                offset=self.offset,
                sort_column=self.sort_column,
                sort_order=self.sort_order,
            )
            elapsed = time.time() - t0
            err = ""
            if rows and "_error" in rows[0]:
                err = rows[0]["_error"]
                rows = []
            self.data_ready.emit(cols, rows, total, elapsed, err)
        except Exception as exc:
            elapsed = time.time() - t0
            self.data_ready.emit([], [], 0, elapsed, str(exc))


class DbView(QWidget):
    """Database explorer, in-cell editor, and Find & Replace control center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_db = "acore_world"
        self.current_table = "item_template"
        self.current_columns: List[str] = []
        self.current_rows: List[Dict[str, Any]] = []
        self.primary_key: Optional[str] = None
        self.current_page = 0
        self.page_size = 500
        self.total_rows = 0

        # Sort state
        self.sort_column: str = ""
        self.sort_order: str = "ASC"

        # Pending dirty edits: (row_idx, col_name) -> (pk_val, new_val)
        self._pending_edits: Dict[Tuple[int, str], Tuple[Any, Any]] = {}
        self._loading_data = False

        self.query_worker: Optional[DbQueryWorker] = None

        self.init_ui()
        self.check_connection_and_init()

    def init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 14, 16, 14)
        root_layout.setSpacing(10)

        # 1. Top Header
        top_header = QHBoxLayout()

        header_title = QLabel("🗄️ AzerothCore Database Explorer")
        header_title.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {TEXT_PRIMARY};")
        top_header.addWidget(header_title)

        top_header.addStretch()

        # Connection status pill
        self.conn_indicator = QLabel("● Database Disconnected")
        self.conn_indicator.setStyleSheet(
            f"padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; "
            f"background-color: rgba(218, 54, 51, 0.2); color: #ff7b72; border: 1px solid rgba(218, 54, 51, 0.4);"
        )
        top_header.addWidget(self.conn_indicator)

        self.btn_reconnect = QPushButton("⚡ Reconnect")
        self.btn_reconnect.setCursor(Qt.PointingHandCursor)
        self.btn_reconnect.clicked.connect(self.check_connection_and_init)
        top_header.addWidget(self.btn_reconnect)

        root_layout.addLayout(top_header)

        # 2. Main Splitter (Left: Table selector, Right: Data Grid & Actions)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {BORDER_SUBTLE}; width: 2px; }}")

        # --- LEFT PANEL: Database & Tables ---
        left_panel = QFrame()
        left_panel.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_lbl = QLabel("DATABASE")
        left_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TEXT_MUTED}; letter-spacing: 1px;")
        left_layout.addWidget(left_lbl)

        self.combo_db = QComboBox()
        self.combo_db.addItems(DB_MGR.CORE_DATABASES)
        self.combo_db.currentTextChanged.connect(self._on_database_changed)
        left_layout.addWidget(self.combo_db)

        # Quick Jump Shortcuts
        shortcuts_lbl = QLabel("QUICK SHORTCUTS")
        shortcuts_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TEXT_MUTED}; letter-spacing: 1px; margin-top: 6px;")
        left_layout.addWidget(shortcuts_lbl)

        self.shortcuts_layout = QVBoxLayout()
        self.shortcuts_layout.setSpacing(4)
        left_layout.addLayout(self.shortcuts_layout)

        # Tables List
        tables_lbl = QLabel("ALL TABLES")
        tables_lbl.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {TEXT_MUTED}; letter-spacing: 1px; margin-top: 6px;")
        left_layout.addWidget(tables_lbl)

        self.table_search_input = QLineEdit()
        self.table_search_input.setPlaceholderText("Filter tables...")
        self.table_search_input.textChanged.connect(self._filter_table_list)
        left_layout.addWidget(self.table_search_input)

        self.table_list = QListWidget()
        self.table_list.currentTextChanged.connect(self._on_table_selected)
        left_layout.addWidget(self.table_list)

        left_panel.setMinimumWidth(210)
        left_panel.setMaximumWidth(260)
        splitter.addWidget(left_panel)

        # --- RIGHT PANEL: Data Table & Find/Replace ---
        right_panel = QFrame()
        right_panel.setStyleSheet(f"background-color: {BG_CARD}; border: 1px solid {BORDER_SUBTLE}; border-radius: 8px;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(8)

        # Table header info & Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.table_title = QLabel("item_template")
        self.table_title.setStyleSheet(f"font-size: 15px; font-weight: 800; color: {GOLD_PRIMARY};")
        toolbar.addWidget(self.table_title)

        self.row_count_badge = QLabel("0 rows")
        self.row_count_badge.setStyleSheet(
            f"background-color: {BG_SURFACE_ALT}; color: {TEXT_SECONDARY}; padding: 2px 8px; border-radius: 4px; font-size: 11px;"
        )
        toolbar.addWidget(self.row_count_badge)

        toolbar.addStretch()

        # Column selector for search
        self.combo_search_col = QComboBox()
        self.combo_search_col.addItem("All columns")
        self.combo_search_col.setMinimumWidth(140)
        self.combo_search_col.setToolTip("Restrict search to this column")
        toolbar.addWidget(self.combo_search_col)

        # Quick search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Quick search...")
        self.search_input.setMinimumWidth(160)
        self.search_input.returnPressed.connect(self.on_search_triggered)
        toolbar.addWidget(self.search_input)

        btn_search = QPushButton("Find")
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.clicked.connect(self.on_search_triggered)
        toolbar.addWidget(btn_search)

        # Page-size selector
        toolbar.addWidget(QLabel("Rows:"))
        self.combo_page_size = QComboBox()
        self.combo_page_size.addItems(["100", "250", "500", "1000"])
        self.combo_page_size.setCurrentText("500")
        self.combo_page_size.setFixedWidth(70)
        self.combo_page_size.currentTextChanged.connect(self._on_page_size_changed)
        toolbar.addWidget(self.combo_page_size)

        # Find & Replace Toggle
        self.btn_toggle_replace = QPushButton("⇄ Find & Replace")
        self.btn_toggle_replace.setCheckable(True)
        self.btn_toggle_replace.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_replace.toggled.connect(self._on_toggle_replace_drawer)
        toolbar.addWidget(self.btn_toggle_replace)

        right_layout.addLayout(toolbar)

        # Find & Replace Drawer (Collapsible)
        self.replace_drawer = QFrame()
        self.replace_drawer.setStyleSheet(
            f"background-color: {BG_SURFACE}; border: 1px solid {BORDER_ACCENT}; border-radius: 6px; padding: 10px;"
        )
        self.replace_drawer.setVisible(False)
        replace_layout = QHBoxLayout(self.replace_drawer)
        replace_layout.setContentsMargins(8, 6, 8, 6)
        replace_layout.setSpacing(10)

        replace_layout.addWidget(QLabel("Column:"))
        self.combo_replace_col = QComboBox()
        self.combo_replace_col.setMinimumWidth(130)
        replace_layout.addWidget(self.combo_replace_col)

        replace_layout.addWidget(QLabel("Find:"))
        self.input_find = QLineEdit()
        self.input_find.setPlaceholderText("Target text...")
        replace_layout.addWidget(self.input_find)

        replace_layout.addWidget(QLabel("Replace:"))
        self.input_replace = QLineEdit()
        self.input_replace.setPlaceholderText("Replacement text...")
        replace_layout.addWidget(self.input_replace)

        self.btn_preview_replace = QPushButton("Preview Matches")
        self.btn_preview_replace.setCursor(Qt.PointingHandCursor)
        self.btn_preview_replace.clicked.connect(self.on_preview_replace)
        replace_layout.addWidget(self.btn_preview_replace)

        self.btn_execute_replace = QPushButton("Replace All")
        self.btn_execute_replace.setCursor(Qt.PointingHandCursor)
        self.btn_execute_replace.setStyleSheet(
            f"background-color: {GOLD_PRIMARY}; color: #0b0f15; font-weight: bold; border-radius: 4px; padding: 6px 12px;"
        )
        self.btn_execute_replace.clicked.connect(self.on_execute_replace)
        replace_layout.addWidget(self.btn_execute_replace)

        right_layout.addWidget(self.replace_drawer)

        # Data Table Grid
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.horizontalHeader().setSortIndicatorShown(True)
        self.data_table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.data_table.cellChanged.connect(self._on_cell_edited)
        right_layout.addWidget(self.data_table)

        # Pagination & Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(10)

        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.setCursor(Qt.PointingHandCursor)
        self.btn_prev.clicked.connect(self.on_prev_page)
        bottom_bar.addWidget(self.btn_prev)

        self.lbl_page = QLabel("Page 1 of 1")
        self.lbl_page.setStyleSheet(f"color: {TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        bottom_bar.addWidget(self.lbl_page)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.clicked.connect(self.on_next_page)
        bottom_bar.addWidget(self.btn_next)

        self.status_info = QLabel("Ready")
        self.status_info.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px; margin-left: 10px;")
        bottom_bar.addWidget(self.status_info)

        bottom_bar.addStretch()

        # Save Pending Changes Button
        self.btn_discard_changes = QPushButton("Discard Edits")
        self.btn_discard_changes.setCursor(Qt.PointingHandCursor)
        self.btn_discard_changes.setEnabled(False)
        self.btn_discard_changes.clicked.connect(self.load_table_data)
        bottom_bar.addWidget(self.btn_discard_changes)

        self.btn_save_changes = QPushButton("💾 Save Changes to DB")
        self.btn_save_changes.setCursor(Qt.PointingHandCursor)
        self.btn_save_changes.setEnabled(False)
        self.btn_save_changes.setStyleSheet(
            f"background-color: {GREEN_ONLINE}; color: #ffffff; font-weight: bold; border-radius: 6px; padding: 7px 16px;"
        )
        self.btn_save_changes.clicked.connect(self.on_save_edits_to_db)
        bottom_bar.addWidget(self.btn_save_changes)

        right_layout.addLayout(bottom_bar)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        root_layout.addWidget(splitter)

    def check_connection_and_init(self):
        """Tests live database connection and refreshes table list."""
        connected, msg = DB_MGR.test_connection(self.current_db)
        if connected:
            self.conn_indicator.setText("● Connected to MySQL (3306)")
            self.conn_indicator.setStyleSheet(
                f"padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; "
                f"background-color: rgba(35, 134, 54, 0.25); color: {GREEN_BRIGHT}; border: 1px solid {GREEN_ONLINE};"
            )
            self._update_quick_shortcuts()
            self._load_table_list()
        else:
            self.conn_indicator.setText("● Database Offline (Boot server first)")
            self.conn_indicator.setStyleSheet(
                f"padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; "
                f"background-color: rgba(218, 54, 51, 0.2); color: #ff7b72; border: 1px solid rgba(218, 54, 51, 0.4);"
            )
            self.status_info.setText(f"Database error: {msg}")

    def _on_database_changed(self, db_name: str):
        self.current_db = db_name
        self._update_quick_shortcuts()
        self._load_table_list()

    def _update_quick_shortcuts(self):
        """Renders quick jump buttons for the selected database."""
        # Clear existing buttons
        while self.shortcuts_layout.count():
            item = self.shortcuts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        shortcuts = DB_MGR.POPULAR_SHORTCUTS.get(self.current_db, [])
        for tbl in shortcuts:
            btn = QPushButton(tbl)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"background-color: {BG_SURFACE}; color: {TEXT_PRIMARY}; border: 1px solid {BORDER_SUBTLE}; "
                f"border-radius: 4px; padding: 4px 8px; text-align: left; font-size: 11px; font-weight: 600;"
            )
            btn.clicked.connect(lambda _, t=tbl: self._select_shortcut_table(t))
            self.shortcuts_layout.addWidget(btn)

    def _select_shortcut_table(self, table_name: str):
        # Find item in table list and select it
        items = self.table_list.findItems(table_name, Qt.MatchExactly)
        if items:
            self.table_list.setCurrentItem(items[0])
        else:
            self._on_table_selected(table_name)

    def _load_table_list(self):
        self.table_list.clear()
        tables = DB_MGR.list_tables(self.current_db)
        self.all_tables = tables
        self.table_list.addItems(tables)

        # If current table in list, select it; otherwise select first
        if self.current_table in tables:
            items = self.table_list.findItems(self.current_table, Qt.MatchExactly)
            if items:
                self.table_list.setCurrentItem(items[0])
        elif tables:
            self.table_list.setCurrentRow(0)

    def _filter_table_list(self, filter_text: str):
        ft = filter_text.strip().lower()
        for i in range(self.table_list.count()):
            item = self.table_list.item(i)
            item.setHidden(ft not in item.text().lower())

    def _on_table_selected(self, table_name: str):
        if not table_name:
            return
        self.current_table = table_name
        self.table_title.setText(table_name)
        self.current_page = 0
        self.sort_column = ""
        self.sort_order = "ASC"

        # Reset search filters so stale queries don't apply to the new table
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.combo_search_col.blockSignals(True)
        self.combo_search_col.setCurrentIndex(0)  # "All columns"
        self.combo_search_col.blockSignals(False)

        self._pending_edits.clear()
        self._update_edit_buttons()
        self.load_table_data()

    def _on_toggle_replace_drawer(self, checked: bool):
        self.replace_drawer.setVisible(checked)

    def on_search_triggered(self):
        self.current_page = 0
        self.load_table_data()

    def _on_page_size_changed(self, value: str):
        try:
            self.page_size = int(value)
        except ValueError:
            self.page_size = 500
        self.current_page = 0
        self.load_table_data()

    def _on_header_clicked(self, logical_index: int):
        """Toggle sort ASC/DESC on clicked column."""
        if logical_index < 0 or logical_index >= len(self.current_columns):
            return
        col_name = self.current_columns[logical_index]
        if self.sort_column == col_name:
            self.sort_order = "DESC" if self.sort_order == "ASC" else "ASC"
        else:
            self.sort_column = col_name
            self.sort_order = "ASC"
        self.current_page = 0
        self.load_table_data()

    def on_prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.load_table_data()

    def on_next_page(self):
        max_page = max(0, (self.total_rows - 1) // self.page_size)
        if self.current_page < max_page:
            self.current_page += 1
            self.load_table_data()

    def load_table_data(self):
        """Asynchronously loads table rows from database."""
        self._loading_data = True
        self.status_info.setText("Fetching table records...")
        offset = self.current_page * self.page_size

        # Resolve selected search column (index 0 = "All columns" sentinel)
        search_col_text = self.combo_search_col.currentText()
        search_column = "" if search_col_text == "All columns" else search_col_text

        self.query_worker = DbQueryWorker(
            db_name=self.current_db,
            table_name=self.current_table,
            search_query=self.search_input.text(),
            search_column=search_column,
            where_clause="",
            limit=self.page_size,
            offset=offset,
            sort_column=self.sort_column,
            sort_order=self.sort_order,
            parent=self,
        )
        self.query_worker.data_ready.connect(self._on_data_loaded)
        self.query_worker.start()

    def _on_data_loaded(self, cols: List[str], rows: List[Dict[str, Any]], total: int, elapsed: float, err: str):
        self._loading_data = True
        self.current_columns = cols
        self.current_rows = rows
        self.total_rows = total
        self.primary_key = DB_MGR.get_primary_key(self.current_db, self.current_table)

        # Update columns dropdowns (search + replace), preserving current selection
        prev_search_col = self.combo_search_col.currentText()
        self.combo_search_col.blockSignals(True)
        self.combo_search_col.clear()
        self.combo_search_col.addItem("All columns")
        self.combo_search_col.addItems(cols)
        idx = self.combo_search_col.findText(prev_search_col)
        self.combo_search_col.setCurrentIndex(idx if idx >= 0 else 0)
        self.combo_search_col.blockSignals(False)

        self.combo_replace_col.clear()
        self.combo_replace_col.addItems(cols)

        # Update Table Widget
        self.data_table.setColumnCount(len(cols))
        self.data_table.setRowCount(len(rows))
        self.data_table.setHorizontalHeaderLabels(cols)

        for r_idx, row_dict in enumerate(rows):
            for c_idx, col_name in enumerate(cols):
                raw_val = row_dict.get(col_name)
                val_str = "" if raw_val is None else str(raw_val)
                item = QTableWidgetItem(val_str)
                # Primary key column slightly distinguished
                if col_name == self.primary_key:
                    item.setForeground(QColor(GOLD_PRIMARY))
                self.data_table.setItem(r_idx, c_idx, item)

        # Update sort indicator on header
        if self.sort_column and self.sort_column in cols:
            sort_idx = cols.index(self.sort_column)
            qt_order = Qt.AscendingOrder if self.sort_order == "ASC" else Qt.DescendingOrder
            self.data_table.horizontalHeader().setSortIndicator(sort_idx, qt_order)
        else:
            self.data_table.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)

        # Update Pagination & Badges
        max_page = max(1, (total + self.page_size - 1) // self.page_size) if total > 0 else 1
        page_display = self.current_page + 1
        self.lbl_page.setText(f"Page {page_display} of {max_page}")
        self.row_count_badge.setText(f"{total:,} records")
        self.btn_prev.setEnabled(self.current_page > 0)
        self.btn_next.setEnabled(page_display < max_page)

        if err:
            self.status_info.setText(f"Query Error: {err}")
            self.status_info.setStyleSheet("color: #ff7b72;")
        else:
            sort_info = f" ↕ {self.sort_column} {self.sort_order}" if self.sort_column else ""
            pk_info = f"PK: {self.primary_key}" if self.primary_key else "No PK"
            self.status_info.setText(f"Fetched {len(rows)} records in {elapsed:.3f}s ({pk_info}){sort_info}")
            self.status_info.setStyleSheet(f"color: {TEXT_MUTED};")

        self._pending_edits.clear()
        self._update_edit_buttons()
        self._loading_data = False

    def _on_cell_edited(self, row: int, col: int):
        if self._loading_data:
            return

        col_name = self.current_columns[col]
        new_val = self.data_table.item(row, col).text()

        # Highlight modified cell in gold
        self.data_table.item(row, col).setBackground(QColor(60, 45, 10))

        # Identify record primary key value
        pk_val = None
        if self.primary_key and self.primary_key in self.current_rows[row]:
            pk_val = self.current_rows[row][self.primary_key]

        self._pending_edits[(row, col_name)] = (pk_val, new_val)
        self._update_edit_buttons()

    def _update_edit_buttons(self):
        count = len(self._pending_edits)
        has_edits = count > 0
        self.btn_save_changes.setEnabled(has_edits)
        self.btn_discard_changes.setEnabled(has_edits)
        if has_edits:
            self.btn_save_changes.setText(f"💾 Save Changes to DB ({count})")
        else:
            self.btn_save_changes.setText("💾 Save Changes to DB")

    def on_save_edits_to_db(self):
        """Applies all pending in-cell edits to MySQL safely."""
        if not self._pending_edits:
            return

        if not self.primary_key:
            QMessageBox.warning(
                self,
                "Cannot Save",
                f"Table '{self.current_table}' does not have an identifiable primary key for direct row updates."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Database Update",
            f"Are you sure you want to commit {len(self._pending_edits)} modified cell(s) to '{self.current_table}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply != QMessageBox.Yes:
            return

        success_count = 0
        errors = []

        for (row_idx, col_name), (pk_val, new_val) in self._pending_edits.items():
            ok, msg = DB_MGR.update_cell(
                db_name=self.current_db,
                table_name=self.current_table,
                primary_key_col=self.primary_key,
                primary_key_val=pk_val,
                target_column=col_name,
                new_value=new_val,
            )
            if ok:
                success_count += 1
            else:
                errors.append(msg)

        if errors:
            QMessageBox.warning(self, "Update Errors", f"Updated {success_count} fields, but errors occurred:\n" + "\n".join(errors[:5]))
        else:
            QMessageBox.information(self, "Changes Saved", f"Successfully committed {success_count} update(s) to '{self.current_table}' in database '{self.current_db}'.")

        self.load_table_data()

    def on_preview_replace(self):
        col = self.combo_replace_col.currentText()
        find_text = self.input_find.text()
        if not find_text:
            QMessageBox.warning(self, "Find & Replace", "Please specify a text pattern to find.")
            return

        ok, msg, cnt = DB_MGR.batch_find_replace(
            db_name=self.current_db,
            table_name=self.current_table,
            target_column=col,
            find_val=find_text,
            replace_val="",
            dry_run=True,
        )
        if ok:
            QMessageBox.information(
                self,
                "Find & Replace Preview",
                f"Found {cnt} matching row(s) containing '{find_text}' in column `{self.current_table}`.`{col}`."
            )
        else:
            QMessageBox.warning(self, "Find Error", msg)

    def on_execute_replace(self):
        col = self.combo_replace_col.currentText()
        find_text = self.input_find.text()
        replace_text = self.input_replace.text()

        if not find_text:
            QMessageBox.warning(self, "Find & Replace", "Please specify a text pattern to find.")
            return

        # Preview first
        _, _, cnt = DB_MGR.batch_find_replace(
            db_name=self.current_db,
            table_name=self.current_table,
            target_column=col,
            find_val=find_text,
            replace_val=replace_text,
            dry_run=True,
        )

        reply = QMessageBox.question(
            self,
            "Confirm Global Replace",
            f"Replace '{find_text}' with '{replace_text}' in `{self.current_table}`.`{col}` across all {cnt} matching records?\n\n"
            "This will directly update the database.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        ok, msg, affected = DB_MGR.batch_find_replace(
            db_name=self.current_db,
            table_name=self.current_table,
            target_column=col,
            find_val=find_text,
            replace_val=replace_text,
            dry_run=False,
        )

        if ok:
            QMessageBox.information(self, "Replacement Completed", f"Replaced values in {affected} row(s) successfully.")
            self.load_table_data()
        else:
            QMessageBox.warning(self, "Replacement Failed", msg)
