del /Q %TEMP%\signed.exe
python client\signtool_client.py -f signtool_emulator\bin\signtool.exe -o %TEMP%\signed.exe -u http://localhost:8080 -t -c default %*
pause
