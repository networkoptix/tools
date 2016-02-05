@ECHO OFF

SET PATH=%ENVIRONMENT%\bin;%PATH%

SET DUMPFILE=%1
IF EXIST temp.txt DEL temp.txt

IF NOT "%DUMPFILE%" == "" (
    goto :UNPACK 
) ELSE (
    SET /p DUMMY = No dump file specified. Press any key to exit...
)    
:UNPACK
    IF EXIST %DUMPFILE% (
        REM This needs to be invoked to be able to pass FOR tokens to external outside-of-the-loop variables (fecking bat) to retrieve buildnumber, branch etc.
        SETLOCAL ENABLEDELAYEDEXPANSION
        REM Removing "sent" prefix
        FOR /F "tokens=1 delims=_" %%I IN ("%DUMPFILE%") DO (
            SET SENT=%%I
        )                 
        IF "!SENT!" == "sent" (
            set SHORT_DUMPFILE=!DUMPFILE:~5!
        ) else (
            set SHORT_DUMPFILE=!DUMPFILE!
        )    
        ECHO Short Dumpfile = !SHORT_DUMPFILE!
        
        REM Finding executable name
        FOR /F "tokens=1 delims=." %%I IN ("!SHORT_DUMPFILE!") DO (
            SET TOKEN=%%I
        )         

        FOR /F "tokens=1-2 delims=_" %%I IN ("!TOKEN!") DO (
            SET FIRST=%%I
            SET SECOND=%%J
        )
        IF "!SECOND!" == "" (
            SET EXECUTABLE=!FIRST!
        ) ELSE (
            SET EXECUTABLE=!FIRST! !SECOND!
        )           
        ECHO Executable Name = !EXECUTABLE!

        REM Finding build number
        FOR /F "tokens=1-8 delims=.-" %%I IN ("!SHORT_DUMPFILE!") DO (
            SET BUILDNUMBER=%%M
            SET CUSTOMIZATION=%%O
        )    

        ECHO Build Number = !BUILDNUMBER!
        ECHO Customization = !CUSTOMIZATION!
        IF "!EXECUTABLE!" == "mediaserver" (
            SET INSTALLTYPE=server
        ) ELSE (
            SET INSTALLTYPE=client
        )
        ECHO Install Type = !INSTALLTYPE! 

        wget -qO - http://beta.networkoptix.com/beta-builds/daily/ | findstr !BUILDNUMBER! > temp.txt
        FOR /F "tokens=2 delims=><" %%I IN (temp.txt) DO SET BUILDBRANCH=%%I
        IF "!BUILDBRANCH!" == "" SET /p DUMMY = The build does not exist on the server ot Internet connection error occurs. Press any key to exit...
        ECHO Build Branch = !BUILDBRANCH!
        
        wget -qO - http://beta.networkoptix.com/beta-builds/daily/!BUILDBRANCH!/!CUSTOMIZATION!/windows/ | findstr !BUILDNUMBER! | findstr !INSTALLTYPE!-only | findstr x64 > temp.txt 
        FOR /F delims^=^"^ tokens^=2 %%I IN (temp.txt) DO SET INSTALLER_FILENAME=%%I
        IF "!INSTALLER_FILENAME!" == "" SET /p DUMMY = The Windows Installer does not exist on the server ot Internet connection error occurs. Press any key to exit...
        ECHO Installer Filename = !INSTALLER_FILENAME!        
        
        wget -qO - http://beta.networkoptix.com/beta-builds/daily/!BUILDBRANCH!/!CUSTOMIZATION!/updates/!BUILDNUMBER! | findstr pdb-all > temp.txt  
        FOR /F delims^=^"^ tokens^=2 %%I IN (temp.txt) DO SET PDBALL_FILENAME=%%I
        IF "!PDBALL_FILENAME!" == "" SET /p DUMMY = The Windows Installer does not exist on the server ot Internet connection error occurs. Press any key to exit...
        ECHO PDB All Filename = !PDBALL_FILENAME!

        wget -qO - http://beta.networkoptix.com/beta-builds/daily/!BUILDBRANCH!/!CUSTOMIZATION!/updates/!BUILDNUMBER! | findstr pdb-apps > temp.txt  
        FOR /F delims^=^"^ tokens^=2 %%I IN (temp.txt) DO SET PDBAPPS_FILENAME=%%I
        IF "!PDBAPPS_FILENAME!" == "" SET /p DUMMY = The Windows Installer does not exist on the server ot Internet connection error occurs. Press any key to exit...
        ECHO PDB Zip Filename = !PDBAPPS_FILENAME!
        
        ECHO Downloading installer...
        IF EXIST !INSTALLER_FILENAME! DEL !INSTALLER_FILENAME!
        wget http://beta.networkoptix.com/beta-builds/daily/!BUILDBRANCH!/!CUSTOMIZATION!/windows/!INSTALLER_FILENAME!
        ECHO Downloading PDB All...
        IF EXIST !PDBALL_FILENAME! DEL !PDBALL_FILENAME!
        wget http://beta.networkoptix.com/beta-builds/daily/!BUILDBRANCH!/!CUSTOMIZATION!/updates/!BUILDNUMBER!/!PDBALL_FILENAME!
        ECHO Downloading PDB Apps...
        IF EXIST !PDBAPPS_FILENAME! DEL !PDBAPPS_FILENAME!
        wget http://beta.networkoptix.com/beta-builds/daily/!BUILDBRANCH!/!CUSTOMIZATION!/updates/!BUILDNUMBER!/!PDBAPPS_FILENAME!
        
        ECHO Unpacking Installer...
        msiexec /a !INSTALLER_FILENAME! /qb TARGETDIR="%~dp0!BUILDNUMBER!"
        
        REM DIR /s /b mediaserver.exe > temp.txt
        REM SET /p EXECUTABLE_DIR=<temp.txt
        REM FOR /f %%i in ('DIR /s /b mediaserver.exe') do set EXECUTABLE_DIR=%%i
        FOR /r %%a in (.) DO @IF EXIST "%%~fa\!EXECUTABLE!.exe" set EXECUTABLE_DIR=%%~fa
        ECHO Media Server folder is "!EXECUTABLE_DIR!"
        
        ECHO Copying and extracting Files...
        copy %DUMPFILE% "!EXECUTABLE_DIR!"
        7z x !PDBALL_FILENAME! -o"!EXECUTABLE_DIR!" -y
        7z x !PDBAPPS_FILENAME! -o"!EXECUTABLE_DIR!" -y        
    ) ELSE (
        SET /p DUMMY = Dump file does not exist in this subdirectory. Press any key to exit...       
    )   