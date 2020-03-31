SET TEMP=_temp
SET SIGNTOOL_DIRECTORY=signtool_emulator\bin
python server\signing_server.py -s %SIGNTOOL_DIRECTORY% -c certs %*
