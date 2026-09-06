"""Live Database Interface for AzerothCore (MySQL/MariaDB).

Provides safe inspection, querying, cell-level editing, and batch find/replace
across AzerothCore databases:
- acore_world (items, creatures, quests, gameobjects)
- acore_characters (characters, guild, inventory, quests)
- acore_auth (accounts, security access, realmlist)
- acore_playerbots (bots data, gear)
"""

from dataclasses import dataclass
import os
import re
from typing import Any, Dict, List, Optional, Tuple

try:
    import pymysql
    import pymysql.cursors
    PYMYSQL_AVAILABLE = True
except ImportError:
    PYMYSQL_AVAILABLE = False

from app.config import CONFIG


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    default_value: Any


class DatabaseManager:
    """Manages connections and safe SQL operations on AzerothCore MySQL container."""

    CORE_DATABASES = (
        "acore_world",
        "acore_characters",
        "acore_auth",
        "acore_playerbots",
    )

    POPULAR_SHORTCUTS = {
        "acore_world": [
            "item_template",
            "creature_template",
            "quest_template",
            "gameobject_template",
            "spell_area",
            "command",
        ],
        "acore_characters": [
            "characters",
            "character_queststatus_rewarded",
            "item_instance",
            "guild",
        ],
        "acore_auth": [
            "account",
            "account_access",
            "realmlist",
        ],
        "acore_playerbots": [
            "playerbots_custom_strategy",
        ],
    }

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 3306,
        user: str = "root",
        password: str = "password",
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password

    def _get_connection(self, db_name: Optional[str] = None):
        if not PYMYSQL_AVAILABLE:
            raise RuntimeError("PyMySQL library is not installed in the active environment.")

        return pymysql.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            database=db_name,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=3,
            read_timeout=15,
            write_timeout=15,
            autocommit=True,
        )

    def test_connection(self, db_name: Optional[str] = None) -> Tuple[bool, str]:
        """Verifies whether the database service is reachable and authenticates."""
        if not PYMYSQL_AVAILABLE:
            return False, "PyMySQL dependency is missing. Run 'pip install pymysql'."
        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT VERSION() AS ver;")
                    res = cursor.fetchone()
                    ver = res.get("ver", "MySQL") if res else "MySQL"
                    return True, f"Connected to {ver} at {self.host}:{self.port}"
        except Exception as exc:
            return False, f"Connection failed: {exc}"

    def list_databases(self) -> List[str]:
        """Lists accessible databases matching AzerothCore naming or available on server."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW DATABASES;")
                    rows = cursor.fetchall()
                    names = [r["Database"] for r in rows if "Database" in r]
                    # Filter or prioritize AzerothCore databases
                    ac_dbs = [db for db in self.CORE_DATABASES if db in names]
                    other_dbs = [db for db in names if db not in self.CORE_DATABASES and db not in ("information_schema", "performance_schema", "sys", "mysql")]
                    return ac_dbs + other_dbs
        except Exception:
            return list(self.CORE_DATABASES)

    def list_tables(self, db_name: str) -> List[str]:
        """Returns all table names within the given database."""
        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SHOW TABLES;")
                    rows = cursor.fetchall()
                    tables = []
                    for r in rows:
                        tables.extend(r.values())
                    return sorted(tables)
        except Exception:
            return []

    def get_table_schema(self, db_name: str, table_name: str) -> List[ColumnInfo]:
        """Retrieves column details including names, types, nullability, and primary key."""
        if not re.match(r"^[A-Za-z0-9_]+$", table_name):
            return []
        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DESCRIBE `{table_name}`;")
                    rows = cursor.fetchall()
                    cols = []
                    for r in rows:
                        cols.append(
                            ColumnInfo(
                                name=r.get("Field", ""),
                                data_type=r.get("Type", ""),
                                is_nullable=r.get("Null", "").upper() == "YES",
                                is_primary_key="PRI" in r.get("Key", "").upper(),
                                default_value=r.get("Default"),
                            )
                        )
                    return cols
        except Exception:
            return []

    def get_primary_key(self, db_name: str, table_name: str) -> Optional[str]:
        """Finds the primary key column name for a table."""
        schema = self.get_table_schema(db_name, table_name)
        for col in schema:
            if col.is_primary_key:
                return col.name
        # Fallback heuristic: entry, id, guid
        names = [c.name for c in schema]
        for candidate in ("entry", "id", "guid", "ID", "Entry"):
            if candidate in names:
                return candidate
        return names[0] if names else None

    def query_table(
        self,
        db_name: str,
        table_name: str,
        search_query: str = "",
        where_clause: str = "",
        limit: int = 100,
        offset: int = 0,
        sort_column: str = "",
        sort_order: str = "ASC",
    ) -> Tuple[List[str], List[Dict[str, Any]], int]:
        """Queries table data with safe text search across columns, pagination, and total count.

        Returns: (column_names, rows, total_matching_count)
        """
        if not re.match(r"^[A-Za-z0-9_]+$", table_name):
            return [], [], 0

        schema = self.get_table_schema(db_name, table_name)
        columns = [c.name for c in schema]
        if not columns:
            return [], [], 0

        where_parts: List[str] = []
        params: List[Any] = []

        # Custom WHERE expression if user supplied one
        if where_clause.strip():
            where_parts.append(f"({where_clause.strip()})")

        # Global quick search filter
        if search_query.strip():
            sq = f"%{search_query.strip()}%"
            # Build search condition across text and numeric columns
            sub_clauses = []
            for col in columns[:15]:  # limit to first 15 columns for search performance
                sub_clauses.append(f"`{col}` LIKE %s")
                params.append(sq)
            if sub_clauses:
                where_parts.append(f"({' OR '.join(sub_clauses)})")

        where_sql = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""

        # Total count query
        count_sql = f"SELECT COUNT(*) AS cnt FROM `{table_name}` {where_sql};"

        # Sorting
        order_sql = ""
        if sort_column and sort_column in columns:
            direction = "DESC" if sort_order.upper() == "DESC" else "ASC"
            order_sql = f"ORDER BY `{sort_column}` {direction}"

        limit_val = max(1, min(limit, 500))
        offset_val = max(0, offset)
        data_sql = f"SELECT * FROM `{table_name}` {where_sql} {order_sql} LIMIT {limit_val} OFFSET {offset_val};"

        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    # Execute count
                    cursor.execute(count_sql, tuple(params))
                    count_res = cursor.fetchone()
                    total_count = count_res.get("cnt", 0) if count_res else 0

                    # Execute data fetch
                    cursor.execute(data_sql, tuple(params))
                    rows = cursor.fetchall()
                    return columns, rows, total_count
        except Exception as exc:
            return columns, [{"_error": str(exc)}], 0

    def update_cell(
        self,
        db_name: str,
        table_name: str,
        primary_key_col: str,
        primary_key_val: Any,
        target_column: str,
        new_value: Any,
    ) -> Tuple[bool, str]:
        """Safely updates a single field on a record identified by its primary key."""
        if not re.match(r"^[A-Za-z0-9_]+$", table_name) or not re.match(r"^[A-Za-z0-9_]+$", target_column):
            return False, "Invalid table or column identifier."

        schema = self.get_table_schema(db_name, table_name)
        col_map = {c.name: c for c in schema}
        if target_column not in col_map:
            return False, f"Column '{target_column}' does not exist in '{table_name}'."

        sql = f"UPDATE `{table_name}` SET `{target_column}` = %s WHERE `{primary_key_col}` = %s LIMIT 1;"

        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (new_value, primary_key_val))
                    return True, f"Successfully updated `{table_name}`.`{target_column}` for row ({primary_key_col}={primary_key_val})."
        except Exception as exc:
            return False, f"Failed to update cell: {exc}"

    def batch_find_replace(
        self,
        db_name: str,
        table_name: str,
        target_column: str,
        find_val: str,
        replace_val: str,
        dry_run: bool = True,
    ) -> Tuple[bool, str, int]:
        """Searches and replaces string values in target column with dry-run support.

        Returns: (success, message, match_or_updated_count)
        """
        if not find_val:
            return False, "Find value cannot be empty.", 0
        if not re.match(r"^[A-Za-z0-9_]+$", table_name) or not re.match(r"^[A-Za-z0-9_]+$", target_column):
            return False, "Invalid table or column identifier.", 0

        # Check column exists
        schema = self.get_table_schema(db_name, table_name)
        if target_column not in [c.name for c in schema]:
            return False, f"Column '{target_column}' does not exist.", 0

        pattern = f"%{find_val}%"

        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    if dry_run:
                        count_sql = f"SELECT COUNT(*) AS cnt FROM `{table_name}` WHERE `{target_column}` LIKE %s;"
                        cursor.execute(count_sql, (pattern,))
                        res = cursor.fetchone()
                        cnt = res.get("cnt", 0) if res else 0
                        return True, f"Found {cnt} matching rows in `{table_name}`.`{target_column}`.", cnt
                    else:
                        update_sql = f"UPDATE `{table_name}` SET `{target_column}` = REPLACE(`{target_column}`, %s, %s) WHERE `{target_column}` LIKE %s;"
                        cursor.execute(update_sql, (find_val, replace_val, pattern))
                        affected = cursor.rowcount
                        return True, f"Replaced occurrences in {affected} rows in `{table_name}`.", affected
        except Exception as exc:
            return False, f"Find/Replace operation failed: {exc}", 0

    def execute_raw_sql(self, db_name: str, sql: str) -> Tuple[bool, str, List[str], List[Dict[str, Any]]]:
        """Executes arbitrary SQL query (SELECT or DDL/DML) and returns results."""
        clean_sql = sql.strip()
        if not clean_sql:
            return False, "Query is empty.", [], []

        is_select = clean_sql.upper().startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN"))

        try:
            with self._get_connection(db_name) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(clean_sql)
                    if is_select:
                        rows = cursor.fetchall()
                        columns = list(rows[0].keys()) if rows else []
                        return True, f"Returned {len(rows)} rows.", columns, rows
                    else:
                        return True, f"Query executed successfully ({cursor.rowcount} rows affected).", [], []
        except Exception as exc:
            return False, f"SQL Error: {exc}", [], []


# Singleton database manager instance
DB_MGR = DatabaseManager()
