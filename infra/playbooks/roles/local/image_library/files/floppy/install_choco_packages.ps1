C:\ProgramData\chocolatey\choco.exe install tortoisehg -y --version 4.1
C:\ProgramData\chocolatey\choco.exe install python2 -y --version 2.7.14
setx PATH "C:\Python27;C:\Python27\Scripts;%PATH%"
C:\ProgramData\chocolatey\choco.exe install rsync -y --version 5.5.0.20180618
C:\ProgramData\chocolatey\choco.exe install git -y --version 2.16.2
setx PATH "%PATH%;C:\Program Files\Git\bin"

C:\ProgramData\chocolatey\choco.exe install dotnet4.6.1 --version 4.6.01055.20170308 -y --verbose
C:\ProgramData\chocolatey\choco.exe install visualstudio2017community --version 15.2.26430.20170605 -y --verbose
C:\ProgramData\chocolatey\choco.exe install visualstudio2017-workload-nativedesktop --version 1.1.1 --package-parameters "--includeOptional" -y --verbose
C:\ProgramData\chocolatey\choco.exe install nuget.commandline -y --verbose --version 4.5.1
C:\ProgramData\chocolatey\choco.exe install windows-sdk-10 -y --verbose --version 10.1.10586.15
setx PATH "%PATH%;C:\Program Files (x86)\Windows Kits\10\Debuggers\x64"
C:\ProgramData\chocolatey\choco.exe install processhacker -y --verbose --version 2.39