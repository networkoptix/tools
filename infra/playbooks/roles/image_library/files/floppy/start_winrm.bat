REM ============================================================================
REM NOTE:
REM This file is extracted from configuration steps found in
REM https://github.com/joefitzgerald/packer-windows (autounattend.xml).
REM There is no local history for following lines and we probably should revise
REM these configuration steps.
REM ============================================================================

REM Win RM Autostart
cmd.exe /c sc config winrm start= auto
REM Start Win RM Service
cmd.exe /c net start winrm
