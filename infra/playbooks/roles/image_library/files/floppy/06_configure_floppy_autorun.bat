REM ============================================================================
REM Add scrip to run floppy autorun.bat (see run_floppy_autorun.bat)
REM on every user logon
REM adoption from https://stackoverflow.com/a/38156615/1243636
REM @iremizov: I heve no clue why these flags (OXEHK) are used.
REM ============================================================================

REM TODO It would be very cool to configure real autorun scripts for floppy
REM drives that fires once disk is inserted.
xcopy a:\run_floppy_autorun.bat C:\ProgramData\Microsoft\Windows\"Start Menu"\Programs\StartUp /O /X /E /H /K
