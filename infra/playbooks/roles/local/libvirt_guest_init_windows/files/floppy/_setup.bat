cmd.exe /c powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force"
C:\Windows\SysWOW64\cmd.exe /c powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force"

powershell -File                a:\setup_networks.ps1
powershell -File                a:\resize_partition.ps1
timeout /t 10
powershell -File                a:\install_packages.ps1
c:\tools\cygwin\bin\bash.exe -l a:\add_default_keys.sh
