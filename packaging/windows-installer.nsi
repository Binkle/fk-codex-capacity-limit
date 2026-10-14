Unicode True
Name "Codex Capacity Watcher"
OutFile "dist\CodexCapacityWatcher-Setup.exe"
InstallDir "$PROGRAMFILES64\Codex Capacity Watcher"
InstallDirRegKey HKLM "Software\Codex Capacity Watcher" "InstallDir"
RequestExecutionLevel admin
Icon "packaging\assets\CodexCapacityWatcher.ico"
UninstallIcon "packaging\assets\CodexCapacityWatcher.ico"
ShowInstDetails show
ShowUninstDetails show
VIProductVersion "0.1.0.0"
VIAddVersionKey "ProductName" "Codex Capacity Watcher"
VIAddVersionKey "CompanyName" "Binkle"
VIAddVersionKey "FileDescription" "Codex capacity watcher"
VIAddVersionKey "FileVersion" "0.1.0"
VIAddVersionKey "LegalCopyright" "Copyright (c) Binkle"

Section "Codex Capacity Watcher" SecApplication
  SetOutPath "$INSTDIR"
  File "dist\CodexCapacityWatcher.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\Codex Capacity Watcher"
  CreateShortCut "$SMPROGRAMS\Codex Capacity Watcher\Codex Capacity Watcher.lnk" "$INSTDIR\CodexCapacityWatcher.exe"
  CreateShortCut "$DESKTOP\Codex Capacity Watcher.lnk" "$INSTDIR\CodexCapacityWatcher.exe"

  WriteRegStr HKLM "Software\Codex Capacity Watcher" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayName" "Codex Capacity Watcher"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "UninstallString" "$INSTDIR\Uninstall.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayIcon" "$INSTDIR\CodexCapacityWatcher.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayVersion" "0.1.0"
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
