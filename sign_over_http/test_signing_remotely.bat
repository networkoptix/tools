del /Q _temp\signed.exe
python client\sign_binary.py -f signtool_emulator\bin\signtool.exe -o _temp\signed.exe -u http://codesign.nxlocal:8080 -t -c default %*
