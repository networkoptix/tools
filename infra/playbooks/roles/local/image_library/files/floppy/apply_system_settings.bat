REM Set Execution Policy 64 Bit
cmd.exe /c powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force"

REM Set Execution Policy 32 Bit
C:\Windows\SysWOW64\cmd.exe /c powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force"

REM Show file extensions in Explorer
%SystemRoot%\System32\reg.exe ADD HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced\ /v HideFileExt /t REG_DWORD /d 0 /f

REM Enable QuickEdit mode
%SystemRoot%\System32\reg.exe ADD HKCU\Console /v QuickEdit /t REG_DWORD /d 1 /f

REM Show Run command in Start Menu
%SystemRoot%\System32\reg.exe ADD HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced\ /v Start_ShowRun /t REG_DWORD /d 1 /f

REM Show Administrative Tools in Start Menu
%SystemRoot%\System32\reg.exe ADD HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Advanced\ /v StartMenuAdminTools /t REG_DWORD /d 1 /f

REM Zero Hibernation File
%SystemRoot%\System32\reg.exe ADD HKLM\SYSTEM\CurrentControlSet\Control\Power\ /v HibernateFileSizePercent /t REG_DWORD /d 0 /f

REM Disable Hibernation Mode
%SystemRoot%\System32\reg.exe ADD HKLM\SYSTEM\CurrentControlSet\Control\Power\ /v HibernateEnabled /t REG_DWORD /d 0 /f

REM Enable Remote Desktop
%SystemRoot%\System32\reg.exe ADD "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\Terminal Server" /v fDenyTSConnections /t REG_DWORD /d 0 /f

REM Disable Application Compatibility
%SystemRoot%\System32\reg.exe ADD "HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows NT\CurrentVersion\AppCompatFlags" /v {de21dff1-3ea2-4465-98dd-0ad4d23b15fd} /t REG_DWORD /d 4 /f

REM Disable UAC
%SystemRoot%\System32\reg.exe ADD "HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v EnableLUA /t REG_DWORD /d 0 /f
%SystemRoot%\System32\reg.exe ADD "HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Policies\System" /v ConsentPromptBehaviorAdmin /t REG_DWORD /d 0 /f

REM Disable Windows Firewall
netsh advfirewall set allprofiles state off

REM Disable Windows Auto Update
%SystemRoot%\System32\reg.exe add "HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update" /v AUOptions /t REG_DWORD /d 1 /f

REM Use platform clock for time keeping
bcdedit /set {default} useplatformclock true

REM Enable Windows Time Service
w32tm /register

REM Sync time from NTP servers
w32tm /config /syncfromflags:MANUAL /manualpeerlist:"1.pool.ntp.org,0x1 2.pool.ntp.org,0x1 3.pool.ntp.org,0x1"

REM Set NTP poll interval
reg add HKLM\SYSTEM\CurrentControlSet\Services\W32Time\TimeProviders\NtpClient /v SpecialPollInterval /t REG_DWORD /d 900 /f

REM Start Windows Time Service when network is available
sc triggerinfo w32time start/networkon stop/networkoff

REM Disable Windows Search Service
sc config WSearch start= disabled

REM Suppress the Network Location Wizard
reg add HKLM\System\CurrentControlSet\Control\Network\NewNetworkWindowOff /f

REM Set jenkins password never expired
WMIC USERACCOUNT WHERE Name='jenkins' SET PasswordExpires=FALSE
