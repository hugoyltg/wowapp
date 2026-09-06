"""Safe Docker and WSL control interface for AzerothCore.

Provides read-only status inspection and conservative server lifecycle operations:
- Non-destructive start (`docker compose up -d`)
- Safe stop (`docker compose stop`, never down or volume pruning)
- Readiness-gated game launch (`D:\\Programs\\WOW_LK\\Wow.exe`)
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import CONFIG
from app.logs import is_worldserver_ready


@dataclass
class ServiceStatus:
    name: str
    service: str
    state: str
    status: str
    ports: str = ""


@dataclass
class DockerStatus:
    wsl_available: bool
    wsl_distro: str
    docker_running: bool
    docker_version: str = "Unknown"
    compose_version: str = "Unknown"
    error_message: Optional[str] = None


def run_wsl_command(
    command: str,
    cwd: Optional[str] = None,
    timeout: int = 30,
    wsl_distro: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Safely executes a bash command inside WSL and returns (exit_code, stdout, stderr)."""
    distro = wsl_distro or CONFIG.wsl_distro
    full_command = f"cd {cwd} && {command}" if cwd else command

    cmd = [
        "wsl",
        "-d",
        distro,
        "--",
        "bash",
        "-lc",
        full_command,
    ]

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=flags,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    except subprocess.TimeoutExpired:
        return -1, "", f"WSL command timed out after {timeout}s"
    except FileNotFoundError:
        return -1, "", "WSL executable ('wsl.exe') was not found on system PATH."
    except Exception as exc:
        return -1, "", f"Unexpected error executing WSL command: {exc}"



def is_wsl_available(wsl_distro: Optional[str] = None) -> bool:
    """Verifies that WSL is responsive and the target distro is accessible."""
    code, stdout, _ = run_wsl_command("echo ok", timeout=10, wsl_distro=wsl_distro)
    return code == 0 and "ok" in stdout


def is_docker_running(wsl_distro: Optional[str] = None) -> bool:
    """Verifies that the Docker daemon inside WSL is running and accepting commands."""
    code, _, _ = run_wsl_command("docker info >/dev/null 2>&1", timeout=15, wsl_distro=wsl_distro)
    return code == 0


def get_docker_status(wsl_distro: Optional[str] = None) -> DockerStatus:
    """Collects comprehensive status of WSL and Docker daemon without modifying anything."""
    distro = wsl_distro or CONFIG.wsl_distro

    if not is_wsl_available(distro):
        return DockerStatus(
            wsl_available=False,
            wsl_distro=distro,
            docker_running=False,
            error_message=f"WSL distribution '{distro}' is not responding.",
        )

    if not is_docker_running(distro):
        return DockerStatus(
            wsl_available=True,
            wsl_distro=distro,
            docker_running=False,
            error_message="Docker daemon is not running inside WSL. Please start Docker service.",
        )

    _, docker_ver, _ = run_wsl_command("docker --version", wsl_distro=distro)
    _, compose_ver, _ = run_wsl_command("docker compose version", wsl_distro=distro)

    return DockerStatus(
        wsl_available=True,
        wsl_distro=distro,
        docker_running=True,
        docker_version=docker_ver or "Docker Installed",
        compose_version=compose_ver or "Compose Installed",
    )


def docker_version() -> str:
    """Legacy helper for backward compatibility."""
    status = get_docker_status()
    if status.docker_running:
        return status.docker_version
    return status.error_message or "Docker not available"


def get_services_status(wsl_distro: Optional[str] = None) -> Dict[str, ServiceStatus]:
    """Queries Docker Compose for container states in a safe, read-only manner."""
    statuses: Dict[str, ServiceStatus] = {}
    for svc in CONFIG.core_services:
        statuses[svc] = ServiceStatus(
            name=svc,
            service=svc,
            state="stopped",
            status="Not running",
        )

    distro = wsl_distro or CONFIG.wsl_distro
    if not is_docker_running(distro):
        return statuses

    code, stdout, _ = run_wsl_command(
        "docker compose ps -a --format json",
        cwd=CONFIG.acore_path,
        wsl_distro=distro,
        timeout=15,
    )

    if code == 0 and stdout:
        try:
            # Output can be either a JSON array or newline-delimited JSON objects
            records = []
            if stdout.startswith("["):
                records = json.loads(stdout)
            else:
                for line in stdout.splitlines():
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))

            for rec in records:
                name = rec.get("Name", "")
                service = rec.get("Service", "")
                state = rec.get("State", "unknown").lower()
                status_str = rec.get("Status", "")
                ports = rec.get("Publishers", "") or rec.get("Ports", "")

                for svc_key in CONFIG.core_services:
                    if svc_key in (name, service):
                        statuses[svc_key] = ServiceStatus(
                            name=name or svc_key,
                            service=service or svc_key,
                            state=state,
                            status=status_str,
                            ports=str(ports),
                        )
        except Exception:
            pass

    return statuses


def start_server(wsl_distro: Optional[str] = None) -> Tuple[bool, str]:
    """Boots the AzerothCore server using `docker compose up -d`.

    Starts all required containers in background, matching user's compose configuration.
    """
    distro = wsl_distro or CONFIG.wsl_distro

    if not is_docker_running(distro):
        return False, "Cannot boot server: Docker is not running in WSL."

    code, stdout, stderr = run_wsl_command(
        "docker compose up -d",
        cwd=CONFIG.acore_path,
        wsl_distro=distro,
        timeout=90,
    )

    if code == 0:
        return True, "Server containers booted successfully."
    else:
        err = stderr or stdout or f"Exited with code {code}"
        return False, f"Failed to boot server: {err}"


def stop_server(wsl_distro: Optional[str] = None) -> Tuple[bool, str]:
    """Safely shuts off the AzerothCore server using `docker compose down`.

    Safely stops and removes containers while keeping all database volumes and data intact.
    """
    distro = wsl_distro or CONFIG.wsl_distro

    if not is_docker_running(distro):
        return False, "Docker is not running in WSL."

    code, stdout, stderr = run_wsl_command(
        "docker compose down",
        cwd=CONFIG.acore_path,
        wsl_distro=distro,
        timeout=60,
    )

    if code == 0:
        return True, "Server containers shut down cleanly. All data preserved."
    else:
        err = stderr or stdout or f"Exited with code {code}"
        return False, f"Failed to stop server: {err}"



def can_enter_game(wsl_distro: Optional[str] = None) -> Tuple[bool, str]:
    """Verifies that all server prerequisites are met before allowing the user to enter game.

    Checks:
    1. Docker daemon is up.
    2. Core services (database, auth, world) are in 'running' state.
    3. Worldserver logs indicate the world is initialized and ready for connections.
    """
    distro = wsl_distro or CONFIG.wsl_distro

    if not is_docker_running(distro):
        return False, "Docker is not running."

    services = get_services_status(distro)
    for svc_name in CONFIG.core_services:
        svc = services.get(svc_name)
        if not svc or svc.state != "running":
            return False, f"Service '{svc_name}' is not running (state: {svc.state if svc else 'unknown'})."

    ready, msg = is_worldserver_ready(distro)
    if not ready:
        return False, msg

    return True, "Server is fully operational and ready for connections."


def launch_wow_client(check_readiness: bool = True) -> Tuple[bool, str]:
    """Launches the WoW 3.3.5 client (D:\\Programs\\WOW_LK\\Wow.exe).

    If check_readiness is True, requires the server to be fully running and ready first.
    """
    if check_readiness:
        allowed, reason = can_enter_game()
        if not allowed:
            return False, f"Cannot enter game yet: {reason}"

    client_path = CONFIG.wow_client_path
    if not os.path.isfile(client_path):
        return False, f"WoW client executable not found at: {client_path}"

    try:
        # Launch detached from current process
        client_dir = str(Path(client_path).parent)
        subprocess.Popen([client_path], cwd=client_dir, creationflags=subprocess.DETACHED_PROCESS)
        return True, f"WoW client launched successfully from {client_path}"
    except Exception as exc:
        return False, f"Failed to launch WoW client: {exc}"