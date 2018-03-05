REM ============================================================================
REM This is entry point for initial configuration steps.
REM All output from commands in this file and scripts included here will be
REM visible _only_ in Windows VM GUI. This output is not available on
REM host machine unless provisioning is not headless.
REM So in order to simplify debug only communication-related bootstrap may be
REM included here.
REM -
REM The order of included files is important when working with packer.
REM Once packer can establish connection, it will start to operate on VM, and
REM may halt or reboot machine while bootstrapping in progress.
REM That's why ssh and winrm shall be enabled in last steps.
REM ============================================================================

cmd.exe /c a:\01_configure_execution_policy.bat
cmd.exe /c a:\02_configure_winrm.bat
cmd.exe /c a:\03_install_choco.bat
cmd.exe /c a:\04_install_openssh.bat
cmd.exe /c a:\05_configure_openssh.bat
cmd.exe /c a:\06_configure_floppy_autorun.bat
cmd.exe /c C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe -File a:\07_configure_openssh.ps1 -AutoStart
cmd.exe /c a:\98_enable_sshd.bat
cmd.exe /c a:\99_enable_winrm.bat
