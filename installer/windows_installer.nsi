Unicode true
!include "MUI2.nsh"
!include "FileFunc.nsh"
!ifndef VERSION
  !define VERSION "1.0.6"
!endif
Name "VXDevSync"
OutFile "dist\vxdevsync_${VERSION}_windows_x64_setup.exe"
InstallDir "$LOCALAPPDATA\Programs\VXDevSync"
RequestExecutionLevel user
ShowInstDetails show
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "VXDevSync"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "FileDescription" "VXDevSync Setup"
VIAddVersionKey "LegalCopyright" "Bui Viet Linh"
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Var UpdateReady
Var UpdateReceipt
Var ParentPID
Var Stage
Var PreviousBackup
Function .onInit
  ${GetParameters} $0
  ${GetOptions} $0 "/PARENT_PID=" $ParentPID
  ${GetOptions} $0 "/UPDATE_READY=" $UpdateReady
  ${GetOptions} $0 "/UPDATE_RECEIPT=" $UpdateReceipt
  StrCmp $ParentPID "" ready
  System::Call 'kernel32::OpenProcess(i 0x00100000, i 0, i $ParentPID) p .r1'
  StrCmp $1 0 unsafe_update
  StrCmp $UpdateReady "" unsafe_update
  StrCmp $UpdateReceipt "" unsafe_update
  ClearErrors
  WriteINIStr "$UpdateReceipt" "Update" "state" "helper_ready"
  WriteINIStr "$UpdateReceipt" "Update" "target" "$INSTDIR"
  WriteINIStr "$UpdateReceipt" "Update" "version" "${VERSION}"
  IfErrors unsafe_update
  ClearErrors
  FileOpen $4 "$UpdateReady" w
  IfErrors unsafe_update
  FileWrite $4 "ready"
  FileClose $4
  System::Call 'kernel32::WaitForSingleObject(p r1, i 30000) i .r2'
  System::Call 'kernel32::CloseHandle(p r1)'
  StrCmp $2 0 ready
  WriteINIStr "$UpdateReceipt" "Update" "state" "parent_exit_timeout"
  Abort "VXDevSync is still running; no files were replaced."
  unsafe_update:
  Abort "Updater readiness receipt is missing; no files were replaced."
  ready:
FunctionEnd
Section
  System::Call 'kernel32::GetCurrentProcessId() i .r3'
  StrCpy $Stage "$INSTDIR.update.$3"
  SetOutPath "$Stage"
  ClearErrors
  File /r "dist\VXDevSync\*.*"
  IfErrors failed
  SetOutPath "$TEMP"
  IfFileExists "$INSTDIR.backup\*.*" 0 no_old_backup
    System::Call 'kernel32::GetTickCount() i .r3'
    StrCpy $PreviousBackup "$INSTDIR.backup.$3"
    ClearErrors
    Rename "$INSTDIR.backup" "$PreviousBackup"
    IfErrors failed
  no_old_backup:
  IfFileExists "$INSTDIR\*.*" 0 install_new
    ClearErrors
    Rename "$INSTDIR" "$INSTDIR.backup"
    IfErrors failed
  install_new:
  ClearErrors
  Rename "$Stage" "$INSTDIR"
  IfErrors rollback
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\VXDevSync"
  CreateShortcut "$SMPROGRAMS\VXDevSync\VXDevSync.lnk" "$INSTDIR\VXDevSync.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXDevSync" "DisplayName" "VXDevSync"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXDevSync" "UninstallString" '"$INSTDIR\Uninstall.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXDevSync" "DisplayVersion" "${VERSION}"
  StrCmp $UpdateReceipt "" no_update_receipt
    WriteINIStr "$UpdateReceipt" "Update" "state" "awaiting_launch_confirmation"
  no_update_receipt:
  ClearErrors
  Exec '"$INSTDIR\VXDevSync.exe"'
  IfErrors launch_failed
  Goto done
  launch_failed:
    IfFileExists "$INSTDIR.backup\*.*" 0 failed
    Rename "$INSTDIR" "$Stage"
    IfErrors failed
    Rename "$INSTDIR.backup" "$INSTDIR"
    StrCmp $UpdateReceipt "" failed
      WriteINIStr "$UpdateReceipt" "Update" "state" "relaunch_failed_rolled_back"
    Goto failed
  rollback:
    Rename "$INSTDIR.backup" "$INSTDIR"
  failed:
    MessageBox MB_OK "Installation failed; the previous application was kept."
    SetErrorLevel 1
    Quit
  done:
SectionEnd
Section "Uninstall"
  RMDir /r "$INSTDIR"
  Delete "$SMPROGRAMS\VXDevSync\VXDevSync.lnk"
  RMDir "$SMPROGRAMS\VXDevSync"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\VXDevSync"
SectionEnd
