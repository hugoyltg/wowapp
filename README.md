# AzerothCore Manager (WoW 3.3.5a)

A modern, clean desktop control center for managing your self-hosted **AzerothCore Wrath of the Lich King (3.3.5a)** server running on Docker and WSL2.

---

## Features

- **One-Click Server Lifecycle**:
  - **Boot Server**: Starts all server containers (`ac-database`, `ac-authserver`, `ac-worldserver`) cleanly in the background via Docker Compose.
  - **Shut Off Server**: Safely stops containers (`docker compose down`) while preserving all databases, character progression, and accounts.
- **Dedicated Worldserver Console**:
  - Live log streaming directly from `ac-worldserver`.
  - Displays bot engine statuses, world ticks, and realm initialization in real time.
- **Live Status Monitoring**:
  - Visual status cards for Database (MySQL 8.4), Authserver (Logon), and Worldserver (Realm).
- **Gated "Enter Game" Action**:
  - Safety gate locks the Play button while the server is offline or booting.
  - Automatically unlocks and lights up as soon as the worldserver signals it is accepting player logins.
  - One-click launch of World of Warcraft 3.3.5a (`D:\Programs\WOW_LK\Wow.exe`).

---

## Quick Start & Virtual Environment

This project uses a dedicated Python virtual environment (`.venv`) to keep your system clean.

### 1. Activating the Virtual Environment

#### On Windows PowerShell:
```powershell
# If your PowerShell blocks script execution, run this once in your session:
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Activate the venv:
.\.venv\Scripts\Activate.ps1
```
When active, your prompt will show `(.venv)` at the beginning.

#### On Windows Command Prompt (cmd.exe):
```cmd
.\.venv\Scripts\activate.bat
```

---

### 2. Installing Dependencies

If setting up for the first time or after pulling updates:
```powershell
pip install -r requirements.txt
```

---

### 3. Launching the App

With the virtual environment activated:
```powershell
python app/main.py
```
*(Or run headless with `python app/main.py --cli` or `python app/main.py --status`).*

---

### 4. Running Automated Tests

```powershell
pytest -v
```

---

### 5. Deactivating the Virtual Environment

When you are done working with the app, simply run:
```powershell
deactivate
```
This restores your terminal back to your standard system Python environment.

---

## Repository

- **GitHub URL**: [https://github.com/hugoyltg/wowapp](https://github.com/hugoyltg/wowapp)

### Pushing to GitHub
Once you have created the empty repository `wowapp` on your GitHub account ([https://github.com/new](https://github.com/new)):
```powershell
git push -u origin main
```

