@echo off
setlocal
cd /d "%~dp0\.."

py -3 -c "import PyInstaller, PySide6" >nul 2>&1
if errorlevel 1 py -3 -m pip install --upgrade pyinstaller PySide6
py -3 -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name CodexCapacityWatcher ^
  --icon packaging\assets\CodexCapacityWatcher.ico ^
  --add-data "packaging\assets\codex-capacity-watcher-icon.png;assets" ^
  --hidden-import codex_capacity_watcher ^
  scripts\codex_capacity_watcher_gui.py

where makensis >nul 2>&1
if errorlevel 1 (
  echo NSIS is required to build the Windows installer. Install it from https://nsis.sourceforge.io/Download
  exit /b 1
)
makensis packaging\windows-installer.nsi

echo Built dist\CodexCapacityWatcher-Setup.exe
