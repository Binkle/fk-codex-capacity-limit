@echo off
setlocal EnableExtensions
pushd "%~dp0\.."
if errorlevel 1 exit /b 1
call :build %*
set "WATCHER_BUILD_EXIT=%ERRORLEVEL%"
popd
exit /b %WATCHER_BUILD_EXIT%

:build
echo [build] Working directory: %CD%
set "WATCHER_PACKAGE_FORMAT=%~1"
if not defined WATCHER_PACKAGE_FORMAT set "WATCHER_PACKAGE_FORMAT=all"
if /i not "%WATCHER_PACKAGE_FORMAT%"=="all" if /i not "%WATCHER_PACKAGE_FORMAT%"=="exe" if /i not "%WATCHER_PACKAGE_FORMAT%"=="msi" (
  echo Usage: packaging\build-windows.bat [all^|exe^|msi] [--skip-app]
  exit /b 1
)
if not "%~2"=="" if /i not "%~2"=="--skip-app" exit /b 1

set "WATCHER_PYTHON="
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 set "WATCHER_PYTHON=python"
if not defined WATCHER_PYTHON (
  py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
  if not errorlevel 1 set "WATCHER_PYTHON=py -3"
)
if not defined WATCHER_PYTHON (
  echo Python 3.10 or later is required to build the Windows application.
  exit /b 1
)
%WATCHER_PYTHON% --version
echo [build] Checking Python build dependencies
%WATCHER_PYTHON% -c "import PyInstaller, PySide6" >nul 2>&1
if errorlevel 1 %WATCHER_PYTHON% -m pip install --upgrade pyinstaller PySide6
if errorlevel 1 (
  echo Failed to install Python build dependencies.
  exit /b 1
)
echo [build] Running PyInstaller
if /i "%~2"=="--skip-app" goto app_built
%WATCHER_PYTHON% -m PyInstaller ^
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
:app_built
if not exist "dist\CodexCapacityWatcher.exe" (
  echo PyInstaller completed without creating dist\CodexCapacityWatcher.exe.
  exit /b 1
)
echo [build] PyInstaller output is present
%WATCHER_PYTHON% packaging\render_windows_installer.py
if errorlevel 1 exit /b 1
if /i "%WATCHER_PACKAGE_FORMAT%"=="msi" goto build_msi

if defined MAKENSIS if exist "%MAKENSIS%" goto nsis_found
set "MAKENSIS=%ProgramFiles(x86)%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" set "MAKENSIS=%ProgramFiles%\NSIS\makensis.exe"
if not exist "%MAKENSIS%" for /f "delims=" %%I in ('where makensis.exe 2^>nul') do set "MAKENSIS=%%I"
if not exist "%MAKENSIS%" (
  echo NSIS is required to build the Windows installer. Install it from https://nsis.sourceforge.io/Download
  exit /b 1
)
:nsis_found
echo Using NSIS: %MAKENSIS%
echo [build] Running NSIS installer compiler
"%MAKENSIS%" packaging\windows-installer.nsi
if errorlevel 1 (
  echo NSIS failed to build the installer.
  exit /b 1
)
if not exist "dist\CodexCapacityWatcher-Setup.exe" (
  echo NSIS completed without creating dist\CodexCapacityWatcher-Setup.exe.
  exit /b 1
)

echo Built dist\CodexCapacityWatcher-Setup.exe
if /i "%WATCHER_PACKAGE_FORMAT%"=="exe" exit /b 0
:build_msi
call packaging\build-windows-msi.bat
if errorlevel 1 exit /b 1
exit /b 0
