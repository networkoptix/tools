REM ============================================================================
REM NOTE:
REM This file is extracted from configuration steps found in
REM https://github.com/joefitzgerald/packer-windows (autounattend.xml).
REM There is no local history for following lines and we probably should revise
REM these configuration steps.
REM ============================================================================


REM winrm quickconfig -q
cmd.exe /c winrm quickconfig -q
REM winrm quickconfig -transport:http
cmd.exe /c winrm quickconfig -transport:http
REM Win RM MaxTimoutms
cmd.exe /c winrm set winrm/config @{MaxTimeoutms="1800000"}
REM Win RM MaxMemoryPerShellMB
cmd.exe /c winrm set winrm/config/winrs @{MaxMemoryPerShellMB="800"}
REM Win RM AllowUnencrypted
cmd.exe /c winrm set winrm/config/service @{AllowUnencrypted="true"}
REM Win RM auth Basic
cmd.exe /c winrm set winrm/config/service/auth @{Basic="true"}
REM Win RM client auth Basic
cmd.exe /c winrm set winrm/config/client/auth @{Basic="true"}
REM Win RM listener Address/Port
cmd.exe /c winrm set winrm/config/listener?Address=*+Transport=HTTP @{Port="5985"}
REM Win RM adv firewall enable
cmd.exe /c netsh advfirewall firewall set rule group="remote administration" new enable=yes
REM Win RM port open
cmd.exe /c netsh firewall add portopening TCP 5985 "Port 5985"
REM Stop Win RM Service
cmd.exe /c net stop winrm
