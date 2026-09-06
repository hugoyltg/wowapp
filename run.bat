@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    start "" ".venv\Scripts\python.exe" app/main.py
) else (
    echo [ERROR] Virtual environment .venv not found.
    echo Please run: python -m venv .venv
    pause
)
