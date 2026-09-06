"""Log inspection and server readiness utilities.

Provides safe, read-only access to container logs and parses worldserver output
to detect when the server has finished initialization.
"""

from typing import Optional, Tuple
from app.config import CONFIG
import subprocess


def get_container_logs(
    service_name: str = "ac-worldserver",
    tail: int = 150,
    wsl_distro: Optional[str] = None,
) -> Tuple[bool, str]:
    """Safely retrieves recent log lines from Docker Compose via WSL.

    Args:
        service_name: Name of the service (default 'ac-worldserver').
        tail: Number of lines to retrieve.
        wsl_distro: WSL distribution name.

    Returns:
        (success, logs_or_error_message)
    """
    distro = wsl_distro or CONFIG.wsl_distro
    tail_count = max(1, min(tail, 2000))

    if service_name in ("All Services (Combined)", "all"):
        inner_cmd = f"cd {CONFIG.acore_path} && docker compose logs --tail {tail_count}"
    else:
        target = service_name or "ac-worldserver"
        inner_cmd = f"cd {CONFIG.acore_path} && docker compose logs --tail {tail_count} --no-log-prefix {target}"


    cmd = [
        "wsl",
        "-d",
        distro,
        "--",
        "bash",
        "-lc",
        inner_cmd,
    ]

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if getattr(subprocess, "CREATE_NO_WINDOW", None) else 0

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
            creationflags=flags,
        )
        if result.returncode != 0:

            err = result.stderr.strip() or f"Process exited with code {result.returncode}"
            # If compose logs failed because containers aren't running yet
            if "no such service" in err.lower() or "not found" in err.lower() or not err:
                return True, "Server is currently stopped. Boot the server to view initialization logs."
            return False, f"Could not read logs: {err}"

        output = result.stdout or result.stderr or "Server is starting... (Waiting for log output)"
        return True, output.strip()

    except subprocess.TimeoutExpired:
        return False, "Timed out waiting for logs."
    except Exception as exc:
        return False, f"Error retrieving logs: {exc}"


def is_worldserver_ready(wsl_distro: Optional[str] = None) -> Tuple[bool, str]:
    """Checks whether ac-worldserver is running and has completed world initialization.

    Returns:
        (is_ready, status_message)
    """
    distro = wsl_distro or CONFIG.wsl_distro
    success, logs = get_container_logs("ac-worldserver", tail=80, wsl_distro=distro)
    if not success:
        return False, f"Worldserver is not responding: {logs}"

    # Search for known readiness indicators in recent log output
    logs_lower = logs.lower()
    for marker in CONFIG.worldserver_ready_markers:
        if marker.lower() in logs_lower:
            return True, "AzerothCore Worldserver is initialized and ready for connections."

    # If log output exists but ready indicator is not found yet
    if "stopped" in logs_lower or "cannot connect" in logs_lower:
        return False, "Server is currently stopped."
    return False, "Worldserver is still booting / initializing databases..."

