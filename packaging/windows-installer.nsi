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
RequestExecutionLevel admin
ManifestDPIAware true
SetCompressor /SOLID lzma
ShowInstDetails nevershow
ShowUninstDetails nevershow
BrandingText " "
VIProductVersion "0.1.10.0"
VIAddVersionKey "ProductName" "Codex Capacity Watcher"
VIAddVersionKey "CompanyName" "Binkle"
VIAddVersionKey "FileDescription" "Codex capacity watcher"
VIAddVersionKey "FileVersion" "0.1.10"
VIAddVersionKey "LegalCopyright" "Copyright (c) Binkle"

!include "windows-installer-ui.nsh"

Section "Codex Capacity Watcher" SecApplication
  SetOutPath "$INSTDIR"
  File "..${SOURCE_SEPARATOR}dist${SOURCE_SEPARATOR}CodexCapacityWatcher.exe"
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  CreateDirectory "$SMPROGRAMS\Codex Capacity Watcher"
  CreateShortCut "$SMPROGRAMS\Codex Capacity Watcher\Codex Capacity Watcher.lnk" "$INSTDIR\CodexCapacityWatcher.exe"
  ${If} $DesktopShortcut == ${BST_CHECKED}
    CreateShortCut "$DESKTOP\Codex Capacity Watcher.lnk" "$INSTDIR\CodexCapacityWatcher.exe"
  ${EndIf}

  WriteRegStr HKLM "Software\Codex Capacity Watcher" "InstallDir" "$INSTDIR"
  WriteRegStr HKLM "${APP_KEY}" "InstallerLanguage" "$LANGUAGE"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayName" "Codex Capacity Watcher"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayIcon" "$INSTDIR\CodexCapacityWatcher.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher" "DisplayVersion" "0.1.10"
  WriteRegStr HKLM "${ARP_KEY}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "${ARP_KEY}" "Publisher" "Binkle"
  WriteRegStr HKLM "${ARP_KEY}" "QuietUninstallString" '"$INSTDIR\Uninstall.exe" /S'
  WriteRegDWORD HKLM "${ARP_KEY}" "NoModify" 1
  WriteRegDWORD HKLM "${ARP_KEY}" "NoRepair" 1
  ; Retire the legacy uninstall registration only after installing successfully.
  SetRegView 32
  DeleteRegKey HKLM "${ARP_KEY}"
  DeleteRegKey HKLM "${APP_KEY}"
  SetRegView 64
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\Codex Capacity Watcher.lnk"
  Delete "$SMPROGRAMS\Codex Capacity Watcher\Codex Capacity Watcher.lnk"
  RMDir "$SMPROGRAMS\Codex Capacity Watcher"
  ; Older versions created shortcuts for the installing user only.
  SetShellVarContext current
  Delete "$DESKTOP\Codex Capacity Watcher.lnk"
  Delete "$SMPROGRAMS\Codex Capacity Watcher\Codex Capacity Watcher.lnk"
  RMDir "$SMPROGRAMS\Codex Capacity Watcher"
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher"
  DeleteRegKey HKLM "Software\Codex Capacity Watcher"
  Delete "$INSTDIR\CodexCapacityWatcher.exe"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir "$INSTDIR"
SectionEnd
