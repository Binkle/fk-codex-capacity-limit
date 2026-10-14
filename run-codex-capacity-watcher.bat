@echo off
setlocal EnableExtensions
pushd "%~dp0"
if errorlevel 1 exit /b 1

set "WATCHER_PYTHON="
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 set "WATCHER_PYTHON=python"
if not defined WATCHER_PYTHON (
  py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
  if not errorlevel 1 set "WATCHER_PYTHON=py -3"
)
if not defined WATCHER_PYTHON (
  echo Python 3.10 or later is required. Install Python or use the packaged application.
  set "WATCHER_EXIT=1"
  goto finish
)

%WATCHER_PYTHON% scripts\codex_capacity_watcher_gui.py %*
set "WATCHER_EXIT=%ERRORLEVEL%"

:finish
popd
if not "%WATCHER_EXIT%"=="0" pause
exit /b %WATCHER_EXIT%
