package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocUtils;
import com.nx.util.*;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

public final class VmsCodeToApiXmlExecutor
    extends Executor
{
    public File vmsPath;
    public File templateApiXmlFile;
    public File outputApiXmlFile;
    public File optionalOutputApiJsonFile; //< Can be null if not needed.

    protected Apidoc apidoc;

    public int execute()
        throws Exception
    {
        System.out.println("apidoctool: parsing apidoc in C++ and inserting into XML");

        System.out.println("    Input: " + templateApiXmlFile);
        try
        {
            apidoc = XmlSerializer.fromDocument(Apidoc.class, XmlUtils.parseXmlFile(templateApiXmlFile));
            ApidocUtils.checkNoFunctionDuplicates(apidoc);
        }
        catch (Exception e)
        {
            throw new Exception("Error loading API xml file " + templateApiXmlFile + ": " + e.getMessage());
        }

        int processedFunctionsCount = 0;
        processedFunctionsCount += processCppFile(params.templateRegistrationCpp(), new TemplateRegistrationMatcher());
        processedFunctionsCount += processCppFile(params.handlerRegistrationCpp(), new HandlerRegistrationMatcher());

        if (processedFunctionsCount == 0)
            System.out.println("    WARNING: No functions were processed.");
        else
            System.out.println("    API functions processed: " + processedFunctionsCount);

        List<String> groupsToSort= new ArrayList<String>();
        groupsToSort.add("System API");
        groupsToSort.add("Server API");
        ApidocUtils.sortGroups(apidoc, groupsToSort);

        XmlUtils.writeXmlFile(outputApiXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApiXmlFile);

        if (optionalOutputApiJsonFile != null)
        {
            final String json = JsonSerializer.toJsonString(apidoc);
            Utils.writeStringToFile(optionalOutputApiJsonFile, json);
            System.out.println("    Output: " + optionalOutputApiJsonFile);
        }

        return processedFunctionsCount;
    }

    protected int processCppFile(String sourceCppFilename, RegistrationMatcher matcher)
        throws Exception
    {
        final File sourceCppFile = new File(vmsPath + sourceCppFilename);
        System.out.println("    Input: " + sourceCppFile);

        SourceCode reader = new SourceCode(sourceCppFile);
        SourceCodeParser parser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount = parser.parseApidocComments(apidoc, matcher);

        return processedFunctionsCount;
    }
}
