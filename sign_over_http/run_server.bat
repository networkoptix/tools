SET TEMP=c:/develop/devtools/sign_over_http/temp
start python3 signing_server.py -s c:/develop/buildenv/packages/windows/signtool/bin -c c:/develop/devtools/sign_over_http/certs %*
