@if not exist netoptix_vms\appserver2\src\connection_factory.OUT.cpp ^
echo ERROR: This script should be run after run-tests.bat ^
    && pause && exit

@xcopy /E /Y /Q netoptix_vms netoptix_vms.TEST\ ^
    || pause && exit
    
@del netoptix_vms.TEST\appserver2\src\connection_factory.cpp ^
    || pause && exit
    
@move netoptix_vms.TEST\appserver2\src\connection_factory.OUT.cpp ^
    netoptix_vms.TEST\appserver2\src\connection_factory.cpp ^
    || pause && exit

java -jar ../out/apidoctool.jar ^
    code-to-xml ^
    -vms-path netoptix_vms.TEST ^
    -template-xml api.TEMPLATE.xml ^
    -output-xml api.OUT.xml ^
    -output-json api.OUT.json ^
    || echo ATTENTION: SCRIPT FAILED && pause && exit

@echo.

@fc /b api.FROM_CPP.xml api.OUT.xml ^
    || echo ATTENTION: SCRIPT FAILED && pause && exit

@del api.OUT.xml
@echo SUCCESS
@pause
