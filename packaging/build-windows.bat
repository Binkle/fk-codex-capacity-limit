@echo off
setlocal
cd /d "%~dp0\.."
echo [build] Working directory: %CD%

where python >nul 2>&1
if errorlevel 1 (
  echo Python 3 is required to build the Windows application.
  exit /b 1
)
python --version
echo [build] Checking Python build dependencies
python -c "import PyInstaller, PySide6" >nul 2>&1
if errorlevel 1 python -m pip install --upgrade pyinstaller PySide6
if errorlevel 1 (
  echo Failed to install Python build dependencies.
  exit /b 1
)
echo [build] Running PyInstaller
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --windowed ^
  --name CodexCapacityWatcher ^
  --icon packaging\assets\CodexCapacityWatcher.ico ^
  --add-data "packaging\assets\codex-capacity-watcher-icon.png;assets" ^
  --hidden-import codex_capacity_watcher ^
  scripts\codex_capacity_watcher_gui.py
if errorlevel 1 (
  echo PyInstaller failed to build CodexCapacityWatcher.exe.
  exit /b 1
)
if not exist "dist\CodexCapacityWatcher.exe" (
  echo PyInstaller completed without creating dist\CodexCapacityWatcher.exe.
  exit /b 1
)
echo [build] PyInstaller output is present

set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" for /f "delims=" %%I in ('where makensis.exe 2^>nul') do set "MAKENSIS=%%I"
if not exist "%MAKENSIS%" (
  echo NSIS is required to build the Windows installer. Install it from https://nsis.sourceforge.io/Download
  exit /b 1
)
echo Using NSIS: %MAKENSIS%
echo [build] Running NSIS installer compiler
"%MAKENSIS%" /DPROJECT_ROOT="%CD%" packaging\windows-installer.nsi
if errorlevel 1 (
  echo NSIS failed to build the installer.
  exit /b 1
)
if not exist "dist\CodexCapacityWatcher-Setup.exe" (
  echo NSIS completed without creating dist\CodexCapacityWatcher-Setup.exe.
  exit /b 1
)

echo Built dist\CodexCapacityWatcher-Setup.exe
