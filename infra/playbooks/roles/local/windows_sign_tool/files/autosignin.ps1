Import-Module C:\ProgramData\chocolatey\helpers\chocolateyInstaller.psm1
Import-Module C:\ProgramData\chocolatey\helpers\chocolateyProfile.psm1
set PATH "C:\tools\cygwin\usr\local\bin;C:\tools\cygwin\bin;C:\tools\cygwin\bin;C:\Python27;C:\Python27\Scripts;C:\Windows\system32;C:\Windows;C:\Windows\System32\Wbem;C:\Windows\System32\WindowsPowerShell\v1.0;C:\ProgramData\chocolatey\bin;C:\Program Files\TortoiseHg;C:\Program Files\Git\cmd;C:\Program Files\Java\jdk1.8.0_162\bin;C:\Program Files (x86)\Xoreax\IncrediBuild;C:\Program Files (x86)\Microsoft Visual Studio\2017\Community\MSBuild\15.0\Bin\amd64;C:\Program Files (x86)\Windows Kits\10\bin\x64;C:\Windows\system32\config\systemprofile\AppData\Local\Microsoft\WindowsApps"
SET PATH "%PATH%;%ALLUSERSPROFILE%\chocolatey\bin;C:\ProgramData\chocolatey\helpers\functions"
$packageName= 'GlobalSign'
$toolsDir   = "$(Split-Path -Parent $MyInvocation.MyCommand.Definition)"
# does not exists
$url        = 'https://www.globalsign.com/support/adobe/GlobalSign_SAC_9.0.msi'
$url64      = 'https://www.globalsign.com/support/adobe/GlobalSign_SAC_9.0-x64.msi'

$packageArgs = @{
  packageName   = $packageName
  fileType      = 'msi'
  url           = $url
  url64bit      = $url64
  silentArgs    = "/qn /norestart"
  validExitCodes= @(0, 3010, 1641)
  softwareName  = 'GlobalSign*'
  # TODO: these chksums are incorrect, but we don't use 32bit
  checksum      = 'd42a5ae560c00c0faa0f672d6295a739'
  checksumType  = 'md5'
  checksum64    = 'd42a5ae560c00c0faa0f672d6295a739'
  checksumType64= 'md5'
}

Install-ChocolateyPackage @packageArgs

REG ADD "HKEY_CURRENT_USER\SOFTWARE\SAFENET\AUTHENTICATION\SAC\GENERAL" /v "SingleLogon" /t REG_DWORD /d "00000001" /f



C:\Python27\python -m pip install pywin32==223
