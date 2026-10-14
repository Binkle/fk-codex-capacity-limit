; File enumeration uses the compiler host's native path separator.
!ifdef NSIS_WIN32_MAKENSIS
  !define SOURCE_SEPARATOR "\"
!else
  !define SOURCE_SEPARATOR "/"
!endif

Unicode True
Name "Codex Capacity Watcher"
OutFile "..${SOURCE_SEPARATOR}dist${SOURCE_SEPARATOR}CodexCapacityWatcher-Setup.exe"
InstallDir "$PROGRAMFILES64\Codex Capacity Watcher"
InstallDirRegKey HKLM "Software\Codex Capacity Watcher" "InstallDir"
RequestExecutionLevel admin
Icon "assets${SOURCE_SEPARATOR}CodexCapacityWatcher.ico"
UninstallIcon "assets${SOURCE_SEPARATOR}CodexCapacityWatcher.ico"
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "0.1.6.0"
VIAddVersionKey "ProductName" "Codex Capacity Watcher"
VIAddVersionKey "CompanyName" "Binkle"
VIAddVersionKey "FileDescription" "Codex capacity watcher"
VIAddVersionKey "FileVersion" "0.1.6"
VIAddVersionKey "LegalCopyright" "Copyright (c) Binkle"

Section "Codex Capacity Watcher" SecApplication
  SetOutPath "$INSTDIR"
  File "..${SOURCE_SEPARATOR}dist${SOURCE_SEPARATOR}CodexCapacityWatcher.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\Codex Capacity Watcher"
  CreateShortCut "$SMPROGRAMS\Codex Capacity Watcher\Codex Capacity Watcher.lnk" "$INSTDIR\CodexCapacityWatcher.exe"
  CreateShortCut "$DESKTOP\Codex Capacity Watcher.lnk" "$INSTDIR\CodexCapacityWatcher.exe"

  WriteRegStr HKLM "Software\Codex Capacity Watcher" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayName" "Codex Capacity Watcher"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayIcon" "$INSTDIR\CodexCapacityWatcher.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayVersion" "0.1.6"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\Codex Capacity Watcher.lnk"
  Delete "$SMPROGRAMS\Codex Capacity Watcher\Codex Capacity Watcher.lnk"
  RMDir "$SMPROGRAMS\Codex Capacity Watcher"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher"
  DeleteRegKey HKLM "Software\Codex Capacity Watcher"
  Delete "$INSTDIR\CodexCapacityWatcher.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
