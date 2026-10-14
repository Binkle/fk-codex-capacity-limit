!include "MUI2.nsh"
!include "LogicLib.nsh"
!include "nsDialogs.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

!define ARTWORK "..${SOURCE_SEPARATOR}build${SOURCE_SEPARATOR}installer-artwork"
!define APP_KEY "Software\Codex Capacity Watcher"
!define ARP_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\Codex Capacity Watcher"
!define MUI_ICON "assets${SOURCE_SEPARATOR}CodexCapacityWatcher.ico"
!define MUI_UNICON "${MUI_ICON}"
!define MUI_WELCOMEFINISHPAGE_BITMAP "${ARTWORK}${SOURCE_SEPARATOR}sidebar.bmp"
!define MUI_UNWELCOMEFINISHPAGE_BITMAP "${MUI_WELCOMEFINISHPAGE_BITMAP}"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_HEADERIMAGE_BITMAP "${ARTWORK}${SOURCE_SEPARATOR}header.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "${MUI_HEADERIMAGE_BITMAP}"
!define MUI_BGCOLOR "FFFFFF"
!define MUI_TEXTCOLOR "172033"
!define MUI_ABORTWARNING
!define MUI_CUSTOMFUNCTION_GUIINIT InitColors
!define MUI_CUSTOMFUNCTION_UNGUIINIT un.InitColors
!define MUI_LANGDLL_REGISTRY_ROOT HKLM
!define MUI_LANGDLL_REGISTRY_KEY "${APP_KEY}"
!define MUI_LANGDLL_REGISTRY_VALUENAME "InstallerLanguage"

Var WelcomeBitmap
Var WelcomeCanvas
Var TitleFont
Var BodyFont
Var OptionsDialog
Var DirectoryInput
Var DesktopCheckbox
Var DesktopShortcut

!define MUI_PAGE_CUSTOMFUNCTION_SHOW WelcomeShow
!define MUI_PAGE_CUSTOMFUNCTION_DESTROYED WelcomeDestroy
!insertmacro MUI_PAGE_WELCOME
Page custom OptionsCreate OptionsLeave
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_TITLE "$(FinishTitle)"
!define MUI_FINISHPAGE_TEXT "$(FinishBody)"
!define MUI_FINISHPAGE_NOREBOOTSUPPORT
!insertmacro MUI_PAGE_FINISH
!define MUI_UNCONFIRMPAGE_TEXT_TOP "$(UninstallBody)"
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English"
!insertmacro MUI_LANGUAGE "SimpChinese"
SetFont "Segoe UI" 9

LangString WelcomeSubtitle ${LANG_ENGLISH} "Install the app, then keep your Codex sessions moving."
LangString WelcomeSubtitle ${LANG_SIMPCHINESE} "安装应用，随时监测并继续你的 Codex 会话。"
LangString InstallFolder ${LANG_ENGLISH} "Install folder"
LangString InstallFolder ${LANG_SIMPCHINESE} "安装目录"
LangString WelcomeHint ${LANG_ENGLISH} "Choose Next to select a folder and install."
LangString WelcomeHint ${LANG_SIMPCHINESE} "点击「下一步」，选择位置并安装。"
LangString OptionsTitle ${LANG_ENGLISH} "Choose where to install"
LangString OptionsTitle ${LANG_SIMPCHINESE} "选择安装位置"
LangString OptionsSubtitle ${LANG_ENGLISH} "Set the installation folder and your shortcut preference."
LangString OptionsSubtitle ${LANG_SIMPCHINESE} "设置安装目录和快捷方式。"
LangString BrowseLabel ${LANG_ENGLISH} "Browse..."
LangString BrowseLabel ${LANG_SIMPCHINESE} "浏览…"
LangString DesktopLabel ${LANG_ENGLISH} "Create a desktop shortcut"
LangString DesktopLabel ${LANG_SIMPCHINESE} "创建桌面快捷方式"
LangString SetupNote ${LANG_ENGLISH} "Available to everyone on this PC.$\r$\nOpen the app after installation to configure your Codex CLI."
LangString SetupNote ${LANG_SIMPCHINESE} "此电脑上的所有用户均可使用。$\r$\n安装后打开应用，配置可用的 Codex CLI。"
LangString InvalidFolder ${LANG_ENGLISH} "Choose a valid installation folder."
LangString InvalidFolder ${LANG_SIMPCHINESE} "请选择有效的安装目录。"
LangString FinishTitle ${LANG_ENGLISH} "Ready to get started"
LangString FinishTitle ${LANG_SIMPCHINESE} "安装完成，准备就绪"
LangString FinishBody ${LANG_ENGLISH} "Codex Capacity Watcher is installed.$\r$\n$\r$\nOpen it from the Start menu, configure your Codex CLI, then choose Start.$\r$\n$\r$\nYou can pause monitoring at any time from the app or the system tray."
LangString FinishBody ${LANG_SIMPCHINESE} "Codex Capacity Watcher 已安装完成。$\r$\n$\r$\n从开始菜单打开应用，配置 Codex CLI，然后点击「启动监控」。$\r$\n$\r$\n你可以随时在应用或系统托盘中暂停监控。"
LangString UninstallBody ${LANG_ENGLISH} "Remove the application and its shortcuts. Your personal settings and session data will be kept."
LangString UninstallBody ${LANG_SIMPCHINESE} "移除应用及其快捷方式，保留个人设置和会话数据。"
LangString Requires64Bit ${LANG_ENGLISH} "This application requires 64-bit Windows."
LangString Requires64Bit ${LANG_SIMPCHINESE} "此应用需要 64 位 Windows。"
LangString MsiPresent ${LANG_ENGLISH} "The MSI edition is already installed. Uninstall it in Windows Settings before switching to the EXE installer."
LangString MsiPresent ${LANG_SIMPCHINESE} "已安装 MSI 版本。请先在 Windows 设置中卸载，再使用 EXE 安装包。"

Function .onInit
  ; Follow the Windows display language, not the regional date/number format.
  System::Call 'kernel32::GetUserDefaultUILanguage() i .r0'
  IntOp $0 $0 & 0x3FF
  StrCpy $LANGUAGE ${LANG_ENGLISH}
  ${If} $0 == 4
    StrCpy $LANGUAGE ${LANG_SIMPCHINESE}
  ${EndIf}
  ${GetParameters} $0
  ${GetOptions} $0 "/LANG=" $1
  ${If} $1 == ${LANG_ENGLISH}
  ${OrIf} $1 == ${LANG_SIMPCHINESE}
    StrCpy $LANGUAGE $1
  ${EndIf}
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "$(Requires64Bit)" /SD IDOK
    Abort
  ${EndIf}
  SetShellVarContext all
  ; Preserve the path chosen in releases that wrote to the 32-bit registry.
  SetRegView 32
  ReadRegStr $0 HKLM "${APP_KEY}" "InstallDir"
  ${If} $0 != ""
    StrCpy $INSTDIR $0
  ${EndIf}
  SetRegView 64
  ReadRegStr $0 HKLM "${APP_KEY}" "InstallDir"
  ${If} $0 != ""
    StrCpy $INSTDIR $0
  ${EndIf}
  ReadRegStr $0 HKLM "${APP_KEY}\MSI" "InstallDir"
  ${If} $0 != ""
    MessageBox MB_ICONSTOP "$(MsiPresent)" /SD IDOK
    Abort
  ${EndIf}
  StrCpy $DesktopShortcut ${BST_CHECKED}
  InitPluginsDir
  File /oname=$PLUGINSDIR\welcome.bmp "${ARTWORK}${SOURCE_SEPARATOR}welcome.bmp"
FunctionEnd

Function WelcomeShow
  ShowWindow $mui.WelcomePage.Image ${SW_HIDE}
  ShowWindow $mui.WelcomePage.Title ${SW_HIDE}
  ShowWindow $mui.WelcomePage.Text ${SW_HIDE}
  ${NSD_CreateBitmap} 0 0 100% 100% ""
  Pop $WelcomeCanvas
  ${NSD_AddStyle} $WelcomeCanvas ${WS_CLIPSIBLINGS}
  ${NSD_SetStretchedImage} $WelcomeCanvas "$PLUGINSDIR\welcome.bmp" $WelcomeBitmap
  CreateFont $TitleFont "Segoe UI" 17 700
  CreateFont $BodyFont "Segoe UI" 10 400
  ${NSD_CreateLabel} 14u 20u 304u 24u "Codex Capacity Watcher"
  Pop $0
  ${NSD_AddStyle} $0 ${SS_CENTER}
  SetCtlColors $0 "172033" "F4F7FB"
  SendMessage $0 ${WM_SETFONT} $TitleFont 1
  ${NSD_CreateLabel} 14u 48u 304u 22u "$(WelcomeSubtitle)"
  Pop $0
  ${NSD_AddStyle} $0 ${SS_CENTER}
  SetCtlColors $0 "475569" "F4F7FB"
  SendMessage $0 ${WM_SETFONT} $BodyFont 1
  ${NSD_CreateLabel} 42u 130u 80u 12u "Capacity Watcher"
  Pop $0
  ${NSD_AddStyle} $0 ${SS_CENTER}
  SetCtlColors $0 "334155" "FFFFFF"
  ${NSD_CreateLabel} 210u 130u 80u 12u "$(InstallFolder)"
  Pop $0
  ${NSD_AddStyle} $0 ${SS_CENTER}
  SetCtlColors $0 "334155" "FFFFFF"
  ${NSD_CreateLabel} 17u 171u 300u 16u "$(WelcomeHint)"
  Pop $0
  ${NSD_AddStyle} $0 ${SS_CENTER}
  SetCtlColors $0 "64748B" "F4F7FB"
  ; A bitmap is a native child window: keep it behind the accessible text controls.
  System::Call 'user32::SetWindowPos(p $WelcomeCanvas, p 1, i 0, i 0, i 0, i 0, i 0x13)'
FunctionEnd

Function InitColors
  SetCtlColors $HWNDPARENT "172033" "FFFFFF"
FunctionEnd

Function un.InitColors
  SetCtlColors $HWNDPARENT "172033" "FFFFFF"
FunctionEnd

Function WelcomeDestroy
  ${NSD_FreeImage} $WelcomeBitmap
  System::Call 'gdi32::DeleteObject(p $TitleFont)'
  System::Call 'gdi32::DeleteObject(p $BodyFont)'
FunctionEnd

Function OptionsCreate
  !insertmacro MUI_HEADER_TEXT "$(OptionsTitle)" "$(OptionsSubtitle)"
  nsDialogs::Create 1018
  Pop $OptionsDialog
  ${If} $OptionsDialog == error
    Abort
  ${EndIf}
  SetCtlColors $OptionsDialog "172033" "FFFFFF"
  ${NSD_CreateLabel} 0 12u 100% 12u "$(InstallFolder)"
  Pop $0
  SetCtlColors $0 "172033" "FFFFFF"
  ${NSD_CreateDirRequest} 0 31u 235u 15u "$INSTDIR"
  Pop $DirectoryInput
  ${NSD_CreateBrowseButton} 242u 30u 58u 17u "$(BrowseLabel)"
  Pop $0
  ${NSD_OnClick} $0 BrowseFolder
  ${NSD_CreateCheckbox} 0 67u 100% 14u "$(DesktopLabel)"
  Pop $DesktopCheckbox
  SetCtlColors $DesktopCheckbox "172033" "FFFFFF"
  ${NSD_SetState} $DesktopCheckbox $DesktopShortcut
  ${NSD_CreateLabel} 0 103u 100% 32u "$(SetupNote)"
  Pop $0
  SetCtlColors $0 "64748B" "FFFFFF"
  nsDialogs::Show
FunctionEnd

Function BrowseFolder
  Pop $0
  ${NSD_GetText} $DirectoryInput $0
  nsDialogs::SelectFolderDialog "$(InstallFolder)" "$0"
  Pop $0
  ${If} $0 != error
    ${NSD_SetText} $DirectoryInput $0
  ${EndIf}
FunctionEnd

Function OptionsLeave
  ${NSD_GetText} $DirectoryInput $0
  ${If} $0 == ""
    MessageBox MB_ICONEXCLAMATION "$(InvalidFolder)"
    Abort
  ${EndIf}
  GetFullPathName $INSTDIR $0
  ${NSD_GetState} $DesktopCheckbox $DesktopShortcut
FunctionEnd

Function un.onInit
  SetRegView 64
  SetShellVarContext all
  !insertmacro MUI_UNGETLANGUAGE
FunctionEnd
