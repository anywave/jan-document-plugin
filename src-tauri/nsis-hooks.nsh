; MOBIUS NSIS Hooks
; Provides Jan v6.8 prerequisite check and MOBIUS lock management

!macro NSIS_HOOK_PREINSTALL
  ; Check for Jan installation in registry (HKCU first, then HKLM)
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\jan" "InstallLocation"
  StrCmp $0 "" 0 jan_found

  ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\jan" "InstallLocation"
  StrCmp $0 "" jan_not_found jan_found

  jan_not_found:
    MessageBox MB_OKCANCEL|MB_ICONEXCLAMATION \
      "Jan AI is not installed.$\n$\nMOBIUS requires Jan AI v0.6.8 or later as a prerequisite.$\nPlease install Jan AI first, then run MOBIUS setup again." \
      IDOK abort_install
    abort_install:
      Abort
    Goto done

  jan_found:
    ; Jan is installed — continue
    DetailPrint "Jan AI found at: $0"

  done:
!macroend

!macro NSIS_HOOK_POSTINSTALL
  ; Write MOBIUS lock registry values
  WriteRegDWORD HKCU "Software\ANYWAVE\MOBIUS" "JanLocked" 1

  ; Store Jan install path for reference
  ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\jan" "InstallLocation"
  StrCmp $0 "" try_hklm write_path

  try_hklm:
    ReadRegStr $0 HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\jan" "InstallLocation"

  write_path:
    StrCmp $0 "" skip_path 0
    WriteRegStr HKCU "Software\ANYWAVE\MOBIUS" "JanInstallPath" "$0"

  skip_path:
    DetailPrint "MOBIUS lock established"
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  ; Remove lock registry values
  DeleteRegValue HKCU "Software\ANYWAVE\MOBIUS" "JanLocked"
  DeleteRegValue HKCU "Software\ANYWAVE\MOBIUS" "JanInstallPath"
  DetailPrint "MOBIUS lock removed"
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  ; Clean up MOBIUS registry key entirely
  DeleteRegKey /ifempty HKCU "Software\ANYWAVE\MOBIUS"
  DeleteRegKey /ifempty HKCU "Software\ANYWAVE"
  DetailPrint "MOBIUS registry cleaned up"
!macroend
