"""Unit tests for DatabaseManager."""

import pytest
from app.database import DatabaseManager


def test_database_manager_defaults():
    mgr = DatabaseManager(host="127.0.0.1", port=3306)
    assert mgr.host == "127.0.0.1"
    assert mgr.port == 3306
    assert "acore_world" in mgr.CORE_DATABASES
    assert "item_template" in mgr.POPULAR_SHORTCUTS["acore_world"]


def test_offline_database_test_connection():
    # Attempting to connect to an unused port should safely return (False, msg)
    mgr = DatabaseManager(host="127.0.0.1", port=65432)
    ok, msg = mgr.test_connection("acore_world")
    assert ok is False
    assert "Connection failed" in msg or "refused" in msg.lower() or "timeout" in msg.lower()


def test_query_table_table_name_validation():
    mgr = DatabaseManager()
    # Malicious or invalid table name containing spaces or quotes
    cols, rows, count = mgr.query_table("acore_world", "bad table; DROP TABLE users;--")
    assert cols == []
    assert rows == []
    assert count == 0


def test_batch_find_replace_validation():
    mgr = DatabaseManager()
    # Empty find text should fail gracefully
    ok, msg, cnt = mgr.batch_find_replace("acore_world", "item_template", "name", "", "New Sword")
    assert ok is False
    assert cnt == 0
    assert "empty" in msg.lower()
