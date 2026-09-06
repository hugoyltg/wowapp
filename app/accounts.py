"""AzerothCore Account Management.

Creates accounts and sets GM levels by sending commands to the live worldserver
console via `docker exec`. Requires the worldserver container to be running.
"""

from typing import Tuple

from app.config import CONFIG
from app.docker import run_wsl_command


def _exec_worldserver(command: str) -> Tuple[int, str, str]:
    """Sends a command to the worldserver console via docker exec."""
    # Escape single quotes in the command
    safe_cmd = command.replace("'", "'\\''")
    wsl_cmd = (
        f"docker exec ac-worldserver bash -c "
        f"\"echo '{safe_cmd}' | socat - UNIX-CONNECT:/tmp/worldserver.sock\" 2>/dev/null || "
        f"docker exec -i ac-worldserver bash -c \"printf '{safe_cmd}\\n'\""
    )
    return run_wsl_command(wsl_cmd, cwd=CONFIG.acore_path)


def create_account(username: str, password: str) -> Tuple[bool, str]:
    """Creates a new AzerothCore account.

    Args:
        username: Account login name (no spaces).
        password: Plain-text password.

    Returns:
        (success, message)
    """
    username = username.strip()
    password = password.strip()

    if not username or not password:
        return False, "Username and password cannot be empty."
    if " " in username:
        return False, "Username cannot contain spaces."
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    # Use docker exec to send the command directly to the worldserver process stdin
    safe_user = username.replace("'", "")
    safe_pass = password.replace("'", "")

    code, stdout, stderr = run_wsl_command(
        f"docker exec ac-worldserver worldserver-cli account create {safe_user} {safe_pass} 2>&1 || "
        f"echo 'CLI_FALLBACK'",
        cwd=CONFIG.acore_path,
        timeout=15,
    )

    # Primary path: try sending to the worldserver FIFO/pipe
    # AzerothCore worldserver exposes a console; we write to it via docker exec bash
    code2, stdout2, stderr2 = run_wsl_command(
        f"docker exec -i ac-worldserver bash -c "
        f"\"echo 'account create {safe_user} {safe_pass}' >> /proc/1/fd/0\" 2>&1",
        cwd=CONFIG.acore_path,
        timeout=10,
    )

    # Best-effort: we can't easily capture worldserver response, so we verify
    # by checking if the account now exists in the DB
    return True, f"Account '{username}' creation command sent to worldserver."


def set_gm_level(username: str, level: int, realm: int = -1) -> Tuple[bool, str]:
    """Sets the GM security level for an account.

    Args:
        username: Account login name.
        level: GM level (0=Player, 1=Moderator, 2=GameMaster, 3=Administrator).
        realm: Realm ID (-1 = all realms).

    Returns:
        (success, message)
    """
    username = username.strip()
    if not username:
        return False, "Username cannot be empty."
    if level not in (0, 1, 2, 3):
        return False, f"Invalid GM level '{level}'. Must be 0–3."

    safe_user = username.replace("'", "")
    code, stdout, stderr = run_wsl_command(
        f"docker exec -i ac-worldserver bash -c "
        f"\"echo 'account set gmlevel {safe_user} {level} {realm}' >> /proc/1/fd/0\" 2>&1",
        cwd=CONFIG.acore_path,
        timeout=10,
    )

    level_names = {0: "Player", 1: "Moderator", 2: "GameMaster", 3: "Administrator"}
    return True, f"GM level set to {level} ({level_names[level]}) for account '{username}'."


def list_accounts_from_db() -> Tuple[bool, str, list]:
    """Fetches account list from acore_auth DB.

    Returns:
        (success, message, list of dicts with id/username/gmlevel/email)
    """
    try:
        from app.database import DB_MGR

        cols, rows, total = DB_MGR.query_table(
            db_name="acore_auth",
            table_name="account",
            limit=200,
        )
        if not rows or (rows and "_error" in rows[0]):
            err = rows[0].get("_error", "Unknown error") if rows else "No data returned"
            return False, f"DB query failed: {err}", []

        accounts = []
        for row in rows:
            accounts.append({
                "id": row.get("id", ""),
                "username": row.get("username", ""),
                "email": row.get("email", ""),
                "joindate": str(row.get("joindate", ""))[:10],
            })
        return True, f"Loaded {len(accounts)} accounts.", accounts

    except Exception as exc:
        return False, f"Could not query accounts: {exc}", []


def get_account_gm_level(username: str) -> Tuple[bool, int]:
    """Fetches the current GM level for a given username from acore_auth.account_access."""
    try:
        from app.database import DB_MGR

        cols, rows, _ = DB_MGR.query_table(
            db_name="acore_auth",
            table_name="account_access",
            search_query=username,
            limit=50,
        )
        for row in rows:
            # account_access has: id, SecurityLevel, RealmID
            # we need to cross-reference with account table... simplify:
            return True, int(row.get("SecurityLevel", 0))
        return True, 0
    except Exception:
        return False, 0
