"""Configuration settings for AzerothCore Manager.

Defines default paths, WSL settings, service names, and game client location.
All paths and service definitions are read-only defaults.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    # WSL 2 distribution hosting Docker and AzerothCore
    wsl_distro: str = "Ubuntu-24.04"

    # Path to AzerothCore repository inside WSL
    acore_path: str = "/home/main/azerothcore/azerothcore-wotlk"

    # Core compose services required for the server
    core_services: tuple[str, ...] = (
        "ac-database",
        "ac-authserver",
        "ac-worldserver",
    )

    # Windows executable path for World of Warcraft 3.3.5a client
    wow_client_path: str = r"D:\Programs\WOW_LK\Wow.exe"

    # Log markers indicating worldserver is fully booted and ready
    worldserver_ready_markers: tuple[str, ...] = (
        "ready for connections",
        "World initialized",
    )


# Singleton configuration instance
CONFIG = AppConfig()
