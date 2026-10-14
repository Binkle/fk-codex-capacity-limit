@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 scripts\codex_capacity_watcher_gui.py
) else (
  python scripts\codex_capacity_watcher_gui.py
)

if errorlevel 1 pause
