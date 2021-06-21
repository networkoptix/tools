@echo off

if [%1] == [--help] goto show_usage
if [%1] == [-h] goto show_usage
if [%1] == [/?] goto show_usage
goto end_show_usage
:show_usage 
echo This script runs cmake configuration stage with the necessary parameters for Windows x64.
echo You may pass additional cmake configuration options via the script arguments.
echo:
echo Usage:
echo 	%~n0%~x0 [^<cmake-generation-args^>]
echo 	or
echo 	%~n0%~x0 [-h^|--help]
exit /b
:end_show_usage

call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvars64.bat"

set customization=metavms
set cloudHost=meta.nxvms.com

set baseDirWithBackslash=%~dp0
set baseDir=%baseDirWithBackslash:~0,-1%

set buildDir=%baseDir%\..\vms_4.3.0_R2_OPEN_windows_x64-build
set conanDir=%baseDir%\conan
set srcDir=%baseDir%\nx\open_candidate
set qtDir=%conanDir%\data\qt\5.15.2\_\_\package\5c53e1c6f36e23a91c9746818393c494757e5d22
set openSslDir=%conanDir%\data\OpenSSL-Fixed\1.1.1i\_\_\package\c86f468b3051ddb1d94e1c6b6fe74d4645707393
set ffmpegDir=%conanDir%\data\ffmpeg\3.1.9\_\_\package\f33cd0d25fae8a874eeed73e22be3b24d878dbcf
set fliteDir=%conanDir%\data\flite\2.2\_\_\package\3fb49604f9c2f729b85ba3115852006824e72cab
set hidapiDir=%conanDir%\data\hidapi\0.10.1\_\_\package\3fb49604f9c2f729b85ba3115852006824e72cab
set RDEP_PACKAGES_DIR=%baseDir%\packages

cmake ^
    -B "%buildDir%" ^
    -G Ninja ^
    -DCMAKE_C_COMPILER=cl.exe ^
    -DCMAKE_CXX_COMPILER=cl.exe ^
    -DtargetDevice=windows_x64 ^
    -DqtDir="%qtDir%" ^
    -DopenSslDir="%openSslDir%" ^
    -DffmpegDir="%ffmpegDir%" ^
    -DfliteDir="%fliteDir%" ^
    -DhidapiDir="%hidapiDir%" ^
    -Dcustomization="%customization%" ^
	-DcloudHost="%cloudHost%" ^
    -DCMAKE_BUILD_TYPE=Release ^
    %* ^
    "%srcDir%"
	  
if %errorlevel% neq 0 exit /b %errorlevel%

echo:
echo CMake configuration succeeded; now building the project.
echo:

cmake --build "%buildDir%"

if %errorlevel% neq 0 exit /b %errorlevel%

echo:
echo Build succeeded.
