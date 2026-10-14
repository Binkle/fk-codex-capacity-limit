@echo off
setlocal
cd /d "%~dp0\.."

py -3 -m pip install --upgrade pyinstaller
py -3 -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name CodexCapacityWatcher ^
  --hidden-import codex_capacity_watcher ^
  scripts\codex_capacity_watcher_gui.py

echo Built dist\CodexCapacityWatcher.exe
