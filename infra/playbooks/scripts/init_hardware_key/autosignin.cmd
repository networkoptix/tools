rem Put this file or link to it to:
rem C:/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp/
rem Assuming C:/autisignin directory exists and contains autosignin.py script


rem Password for hardware USB signing key:
set KEY_PASSWORD=<password>

rem used: 'where.exe' from from C:\Windows\system32
rem used: 'signtool.exe' from from C:\Program Files (x86)\Windows Kits\10\bin\x64
set PATH=C:\Windows\system32;C:\Windows;C:\Program Files (x86)\Windows Kits\10\bin\x64

cd /d C:\autosignin
C:\Python27\python C:\autosignin\autosignin.py >> C:\autosignin\autosignin.log
