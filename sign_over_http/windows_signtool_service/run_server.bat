SET TEMP=_temp
SET SIGNTOOL_DIRECTORY=%RDEP_PACKAGES_DIR%\windows\signtool\bin
python server\signing_server.py -s %SIGNTOOL_DIRECTORY% -c certs %*
