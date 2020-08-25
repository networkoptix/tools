SET TEMP=_temp
python server\openssl_signing_server.py -k server/private.pem %*
pause
