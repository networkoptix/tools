java -jar ../out/apidoctool.jar ^
    sort-xml ^
    -group-name "System API" ^
    -source-xml api.xml ^
    -output-xml api.OUT.xml ^
    || echo FAILED && pause && exit

@echo.

@fc /b api.SORTED.xml api.OUT.xml ^
    || echo ATTENTION: SCRIPT FAILED && pause && exit
        
@del api.OUT.xml
@echo SUCCESS
@pause
