!macro NSIS_HOOK_POSTINSTALL
  nsExec::ExecToLog 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\resources\install-cli.ps1" -SourceCli "$INSTDIR\resources\opencode.exe"'
  Pop $0
  ${If} $0 != 0
    MessageBox MB_ICONEXCLAMATION "OpenCode could not be added to PATH. PythonTutor is installed; see the installation log."
  ${EndIf}
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::ExecToLog 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$INSTDIR\resources\install-cli.ps1" -SourceCli "$INSTDIR\resources\opencode.exe" -Remove'
  Pop $0
!macroend
