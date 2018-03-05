REM ============================================================================
REM NOTE:
REM This file is extracted from configuration steps found in
REM https://github.com/joefitzgerald/packer-windows (autounattend.xml).
REM There is no local history for following lines and we probably should revise
REM these configuration steps.
REM ============================================================================

REM Set Execution Policy 64 Bit
cmd.exe /c powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force"
REM Set Execution Policy 32 Bit
C:\Windows\SysWOW64\cmd.exe /c powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force"
