@echo off
setlocal EnableExtensions
pushd "%~dp0\.."
if errorlevel 1 exit /b 1
call :build
set "WATCHER_MSI_EXIT=%ERRORLEVEL%"
popd
exit /b %WATCHER_MSI_EXIT%

:build
if not exist "dist\CodexCapacityWatcher.exe" (
  echo Build the application first with packaging\build-windows.bat.
  exit /b 1
)
if not exist "build\installer-artwork\msi-welcome.bmp" (
  echo Render the installer artwork with packaging\render_windows_installer.py first.
  exit /b 1
)
if not defined DOTNET_ROLL_FORWARD set "DOTNET_ROLL_FORWARD=Major"
if not defined WATCHER_WIX (
  dotnet tool restore
  if errorlevel 1 exit /b 1
)
if not defined WATCHER_WIX_UI (
  call :wix extension add WixToolset.UI.wixext/5.0.2
  if errorlevel 1 exit /b 1
  set "WATCHER_WIX_UI=WixToolset.UI.wixext/5.0.2"
)
rem Windows Installer cannot create databases on a WSL share or a mapped UNC drive.
rem Keep intermediate MSI databases on a native Windows volume, then copy outputs.
set "WATCHER_MSI_STAGE=%TEMP%\codex-capacity-msi-%RANDOM%-%RANDOM%"
if exist "%WATCHER_MSI_STAGE%" exit /b 1
mkdir "%WATCHER_MSI_STAGE%"
if errorlevel 1 exit /b 1
echo [build] Building MSI
call :wix build packaging\windows-installer.wxs packaging\windows-installer-ui.wxs ^
  -arch x64 -culture en-US -loc packaging\windows-installer.wxl ^
  -ext "%WATCHER_WIX_UI%" -intermediatefolder "%WATCHER_MSI_STAGE%\obj" ^
  -o "%WATCHER_MSI_STAGE%\CodexCapacityWatcher-Setup.msi"
if errorlevel 1 goto failed
if not exist "%WATCHER_MSI_STAGE%\CodexCapacityWatcher-Setup.msi" goto failed
copy /y "%WATCHER_MSI_STAGE%\CodexCapacityWatcher-Setup.msi" "dist\CodexCapacityWatcher-Setup.msi" >nul
if errorlevel 1 goto failed
rem Remove superseded build outputs so the distribution contains one MSI.
if exist "dist\CodexCapacityWatcher-Setup-en-US.msi" del /q "dist\CodexCapacityWatcher-Setup-en-US.msi"
if exist "dist\CodexCapacityWatcher-Setup-zh-CN.msi" del /q "dist\CodexCapacityWatcher-Setup-zh-CN.msi"
rmdir /s /q "%WATCHER_MSI_STAGE%"
exit /b 0

:failed
echo MSI build files kept at: %WATCHER_MSI_STAGE%
exit /b 1

:wix
if defined WATCHER_WIX (
  "%WATCHER_WIX%" %*
) else (
  dotnet tool run wix -- %*
)
exit /b %ERRORLEVEL%
