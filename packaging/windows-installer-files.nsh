; Check before changing files, shortcuts, or uninstall registrations. Opening an
; existing file without truncation also catches a watcher hidden in the tray.
!macro DefineApplicationFileCheck Prefix
Function ${Prefix}CheckApplicationWritable
  Push $0
  Push $1
retry:
  IfFileExists "$INSTDIR\CodexCapacityWatcher.exe" 0 done
  System::Call 'kernel32::CreateFileW(w "$INSTDIR\CodexCapacityWatcher.exe", i 0x40000000, i 0, p 0, i 3, i 0x80, p 0) p .r0 ?e'
  Pop $1
  ${If} $0 != -1
    System::Call 'kernel32::CloseHandle(p r0)'
    Goto done
  ${EndIf}
  DetailPrint "$(ApplicationFileBusy) (Windows error $1)"
  IfSilent cancel
  MessageBox MB_RETRYCANCEL|MB_ICONEXCLAMATION "$(ApplicationFileBusy)" /SD IDCANCEL IDRETRY retry
cancel:
  SetErrorLevel $1
  Pop $1
  Pop $0
  Abort
done:
  Pop $1
  Pop $0
FunctionEnd
!macroend

!insertmacro DefineApplicationFileCheck ""
!insertmacro DefineApplicationFileCheck "un."
