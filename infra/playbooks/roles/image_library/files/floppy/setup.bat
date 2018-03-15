REM ============================================================================
REM This is entry point for initial setup steps.
REM All output from commands in during initial steps are only visible in Windows
REM VM GUI. This output is not available on host machine unless provisioning is
REM not headless.
REM This entry point starts sole command on target vm and redirects all output
REM into log file on VM.
REM ============================================================================

cmd.exe /c a:\_setup.bat >> c:\setup.log
