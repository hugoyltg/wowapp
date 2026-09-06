"""UI component tests for Sidebar, ConfigView, and DbView."""

import pytest
from PySide6.QtWidgets import QApplication

from ui.components.config_view import ConfigView
from ui.components.db_view import DbView
from ui.components.sidebar import Sidebar
from ui.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sidebar_navigation(qapp):
    sidebar = Sidebar()
    emitted = []
    sidebar.page_changed.connect(lambda idx: emitted.append(idx))

    assert len(sidebar.nav_buttons) == 3
    # Click second item (Game Config)
    sidebar.nav_buttons[1].click()
    assert 1 in emitted

    # Click third item (Database)
    sidebar.nav_buttons[2].click()
    assert 2 in emitted


def test_config_view_initialization(qapp):
    view = ConfigView()
    assert view.pill_group.buttons() is not None
    assert len(view.pill_group.buttons()) == 4

    # Switch category to world
    view.pill_group.button(1).click()
    assert view._current_category == "world"


def test_db_view_initialization(qapp):
    db_view = DbView()
    assert db_view.combo_db.count() >= 4
    assert db_view.btn_save_changes.isEnabled() is False
    assert db_view.btn_discard_changes.isEnabled() is False


def test_main_window_stacked_navigation(qapp):
    win = MainWindow()
    assert win.stacked_widget.count() == 3

    # Switch page via sidebar
    win.sidebar.select_page(1)
    assert win.stacked_widget.currentIndex() == 1

    win.sidebar.select_page(2)
    assert win.stacked_widget.currentIndex() == 2

    # Clean shutdown of test window and worker
    win.poll_worker.stop()
    win.poll_worker.wait(2000)
    win.close()
