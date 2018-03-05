REM @iremizov: This didn't work. Probably the problem was in choco install..
REM netsh advfirewall firewall add rule name=sshd dir=in action=allow protocol=TCP localport=22
REM net start sshd
REM cmd.exe /c powershell -Command "Set-Service sshd -StartupType Automatic"
REM cmd.exe /c powershell -Command "Set-Service ssh-agent -StartupType Automatic"
