@echo off

call clean.bat

echo ===========================================================================
echo suppress-pause | call run-help.bat || pause && exit
echo ===========================================================================
echo suppress-pause | call run-test.bat || pause && exit
echo ===========================================================================
echo suppress-pause | call run-sort-xml.bat || pause && exit
echo ===========================================================================
echo suppress-pause | call run-xml-to-code.bat || pause && exit
echo ===========================================================================
echo suppress-pause | call run-code-to-xml.bat || pause && exit
echo ===========================================================================
echo ALL SCRIPTS SUCCEEDED
pause
