cd ..

move test\api.xml test\api_UNSORTED.xml
if %errorlevel% neq 0 exit /b %errorlevel%

java -jar out/apidoctool.jar -sort-xml "System API" test/api_UNSORTED.xml test/api.xml

pause
