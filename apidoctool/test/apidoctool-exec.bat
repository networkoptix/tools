@set PWD=%~p0
@set API_XML=%CD%\mediaserver_core\x64\additional-resources\static\api.xml
@set API_TEMPLATE_XML=%CD%\mediaserver_core\api\api_template.xml

@if NOT exist %API_TEMPLATE_XML% (
    @echo Run this script from "netoptix_vms" folder.
    @echo ERROR: Cannot open file:
    @echo %API_TEMPLATE_XML%
    @pause
    exit 1
)

@echo Executing apidoctool in %CD%

java -jar %PWD%\..\out\apidoctool.jar code-to-xml -vms-path %CD% -template-xml %API_TEMPLATE_XML% -output-xml %API_XML%

@pause
