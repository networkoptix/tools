REM ============================================================================
REM This is entry point for initial configuration steps.
REM The order of included files is important when working with packer.
REM Once packer can establish connection, it will start to operate on VM, and
REM may halt or reboot machine while bootstrapping in progress.
REM That's why ssh and winrm shall be enabled in last steps.
REM ============================================================================

cmd.exe /c                      a:\apply_system_settings.bat
cmd.exe /c                      a:\install_chocolatey.bat
powershell -File                a:\install_choco_packages.ps1
powershell -File                a:\install_python_packages.ps1
powershell -File                a:\install_cygwin.ps1
c:\tools\cygwin\bin\bash.exe -l a:\configure_cygwin.sh
powershell -File                a:\install_python.ps1
powershell -File                a:\install_java.ps1
powershell -File                a:\install_vs2017ce.ps1
cmd.exe /c                      a:\configure_winrm.bat
cmd.exe /c                      a:\configure_login_items.bat
c:\tools\cygwin\bin\bash.exe -l a:\configure_sshd.sh

c:\tools\cygwin\bin\bash.exe -l a:\start_sshd.sh
cmd.exe /c                      a:\starts_winrm.bat
