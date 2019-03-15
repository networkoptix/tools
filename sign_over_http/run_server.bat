SET TEMP=c:/develop/devtools/sign_over_http/temp
SET SIGNTOOL_DIRECTORY=%RDEP_PACKAGES_DIR%/windows/signtool/bin
start python3 signing_server.py -s %SIGNTOOL_DIRECTORY% -c ./certs -l temp/log.txt %*
