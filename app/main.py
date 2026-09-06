"""Main CLI and interactive entry point for AzerothCore Manager."""

import argparse
import sys
from pathlib import Path

# Ensure the workspace root is in sys.path when executed directly
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from app.config import CONFIG
from app.docker import (
    can_enter_game,
    get_docker_status,
    get_services_status,
    launch_wow_client,
    start_server,
    stop_server,
)
from app.logs import get_container_logs, is_worldserver_ready


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def cmd_status():
    print_header("AZEROTHCORE SERVER STATUS")

    print("[1] Host & Docker Subsystem:")
    d_status = get_docker_status()
    wsl_state = "Available" if d_status.wsl_available else "NOT RESPONDING"
    print(f"  * WSL Distro:      {d_status.wsl_distro} ({wsl_state})")
    daemon_state = "Running" if d_status.docker_running else "STOPPED"
    print(f"  * Docker Daemon:   {daemon_state}")
    if d_status.docker_running:
        print(f"  * Docker Version:  {d_status.docker_version}")
        print(f"  * Compose Version: {d_status.compose_version}")
    elif d_status.error_message:
        print(f"  * Issue:           {d_status.error_message}")

    print("\n[2] Core Server Services:")
    services = get_services_status()
    for svc_name in CONFIG.core_services:
        svc = services.get(svc_name)
        if not svc:
            print(f"  * {svc_name:<18}: NOT CONFIGURED")
            continue

        tag = "[RUNNING]" if svc.state == "running" else "[STOPPED]"
        details = svc.status or svc.state
        print(f"  * {tag:<10} {svc.name:<16}: {details}")

    print("\n[3] Game Readiness Gate:")
    ready, reason = can_enter_game()
    if ready:
        print("  * [READY] ENTER GAME: Server is fully booted and accepting player connections.")
    else:
        print(f"  * [WAITING] NOT READY YET: {reason}")

    print("\n[4] WoW Client Executable:")
    client_exists = Path(CONFIG.wow_client_path).is_file()
    print(f"  * Path: {CONFIG.wow_client_path} ({'Found' if client_exists else 'NOT FOUND'})")



# Try to reconfigure standard streams to UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def cmd_start():
    print_header("BOOTING AZEROTHCORE SERVER")
    print("Issuing non-destructive startup (`docker compose up -d`)...\n")
    success, msg = start_server()
    if success:
        print(f"[OK] {msg}")
        print("Containers are starting. You can monitor startup progress via logs.")
    else:
        print(f"[ERROR] {msg}")


def cmd_stop():
    print_header("SHUTTING OFF AZEROTHCORE SERVER")
    print("Safely halting containers (`docker compose stop`)...\n")
    success, msg = stop_server()
    if success:
        print(f"[OK] {msg}")
    else:
        print(f"[ERROR] {msg}")


def cmd_logs(service: str = "ac-worldserver", tail: int = 50):
    print_header(f"RECENT LOGS FOR {service} (Last {tail} lines)")
    success, output = get_container_logs(service, tail=tail)
    if success:
        print(output)
    else:
        print(f"[ERROR] {output}")


def cmd_enter_game():
    print_header("LAUNCHING WORLD OF WARCRAFT 3.3.5")
    allowed, reason = can_enter_game()
    if not allowed:
        print("[WARNING] [SAFETY GATE] Enter Game is currently blocked:")
        print(f"    {reason}")
        print("\nTip: Boot the server first and wait for world initialization before entering game.")
        return

    print("[OK] Server readiness confirmed!")
    success, msg = launch_wow_client(check_readiness=False)
    if success:
        print(f"[GAME] {msg}")
    else:
        print(f"[ERROR] {msg}")


def interactive_menu():
    while True:
        print("\n" + "=" * 50)
        print("         AZEROTHCORE MANAGER (Phase 1)")
        print("=" * 50)
        print("  [1] Check Server & Docker Status")
        print("  [2] Boot Server (Safe Start)")
        print("  [3] Shut Off Server (Safe Stop)")
        print("  [4] View Recent Worldserver Logs")
        print("  [5] View Recent Authserver Logs")
        print("  [6] Enter Game (Launch WoW 3.3.5)")
        print("  [0] Exit")
        print("-" * 50)

        try:
            choice = input("Select an option (0-6): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "1":
            cmd_status()
        elif choice == "2":
            cmd_start()
        elif choice == "3":
            cmd_stop()
        elif choice == "4":
            cmd_logs("ac-worldserver", tail=40)
        elif choice == "5":
            cmd_logs("ac-authserver", tail=30)
        elif choice == "6":
            cmd_enter_game()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid selection. Please enter a number between 0 and 6.")



def run_gui():
    """Launches the PySide6 Graphical User Interface."""
    try:
        from PySide6.QtWidgets import QApplication
        from ui.main_window import MainWindow

        app = QApplication(sys.argv)
        app.setApplicationName("AzerothCore Manager")

        window = MainWindow()
        window.show()

        sys.exit(app.exec())
    except ImportError as err:
        print(f"[ERROR] Could not load PySide6 GUI framework: {err}")
        print("Falling back to terminal interactive menu...")
        interactive_menu()
    except Exception as exc:
        print(f"[ERROR] Error starting GUI: {exc}")
        print("Falling back to terminal interactive menu...")
        interactive_menu()


def main():
    parser = argparse.ArgumentParser(
        description="AzerothCore Manager - Safe Machine & Docker Controller"
    )
    parser.add_argument("--cli", action="store_true", help="Launch interactive terminal menu instead of GUI")
    parser.add_argument("--status", action="store_true", help="Display server and Docker status")
    parser.add_argument("--start", action="store_true", help="Boot the server containers")
    parser.add_argument("--stop", action="store_true", help="Safely shut off the server containers")
    parser.add_argument(
        "--logs",
        nargs="?",
        const="ac-worldserver",
        help="View recent logs for a container (default: ac-worldserver)",
    )
    parser.add_argument("--tail", type=int, default=50, help="Number of log lines to view")
    parser.add_argument("--enter-game", action="store_true", help="Launch the WoW client (if server is ready)")

    args = parser.parse_args()

    # If specific command flags were provided, run non-interactively
    if args.status:
        cmd_status()
    elif args.start:
        cmd_start()
    elif args.stop:
        cmd_stop()
    elif args.logs:
        cmd_logs(args.logs, tail=args.tail)
    elif args.enter_game:
        cmd_enter_game()
    elif args.cli:
        interactive_menu()
    else:
        # Default: Launch modern Desktop GUI
        run_gui()


if __name__ == "__main__":
    main()
