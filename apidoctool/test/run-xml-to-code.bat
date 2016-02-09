java -jar ../out/apidoctool.jar ^
    xml-to-code ^
    -vms-path netoptix_vms ^
    -source-xml api.xml ^
    -output-xml api.OUT.xml ^
    || echo FAILED && pause && exit

@echo.

@fc /b  api.TEMPLATE.xml api.OUT.xml ^
    || echo ATTENTION: SCRIPT FAILED && pause && exit

@echo SUCCESS
@pause
