package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocUtils;
import com.nx.apidoc.TypeManager;
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
    public File optionalOutputOpenApiJsonFile; //< Can be null if not needed.

    protected Apidoc apidoc;

    public int execute()
        throws Exception
    {
        System.out.println("apidoctool: parsing apidoc in C++ and inserting into XML");

        System.out.println("    Input: " + templateApiXmlFile);
        System.out.println("    Input: " + vmsPath + vmsPath.separatorChar);
        try
        {
            apidoc = XmlSerializer.fromDocument(
                Apidoc.class, XmlUtils.parseXmlFile(templateApiXmlFile));
            ApidocUtils.checkNoFunctionDuplicates(apidoc);
        }
        catch (Exception e)
        {
            throw new Exception("Error loading API xml file " + templateApiXmlFile + ": "
                + e.getMessage());
        }

        TypeManager typeManager = null;
        if (!params.typeHeaderPaths().isEmpty())
        {
            List<File> typeHeaders = Utils.getHeaderFileList(vmsPath, params.typeHeaderPaths());
            typeManager = new TypeManager(verbose);
            typeManager.processFiles(typeHeaders);
        }

        int processedFunctionsCount = 0;
        processedFunctionsCount += processCppFile(
            params.templateRegistrationCpp(),
            new TemplateRegistrationMatcher(),
            typeManager);
        processedFunctionsCount += processCppFile(
            params.handlerRegistrationCpp(),
            new HandlerRegistrationMatcher(),
            typeManager);
        processedFunctionsCount += processCppFile(
            params.templateRegistrationCpp(),
            new HandlerRegistrationMatcher(),
            typeManager);

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

        if (optionalOutputOpenApiJsonFile != null)
        {
            final String json = OpenApiSerializer.toString(apidoc);
            Utils.writeStringToFile(optionalOutputOpenApiJsonFile, json);
            System.out.println("    Output: " + optionalOutputOpenApiJsonFile);
        }

        return processedFunctionsCount;
    }

    private int processCppFile(
        String sourceCppFilename, RegistrationMatcher matcher, TypeManager typeManager)
        throws Exception
    {
        final File sourceCppFile = new File(vmsPath, sourceCppFilename);
        if (verbose)
            System.out.println("    Parsing API functions from " + sourceCppFile);

        SourceCode reader = new SourceCode(sourceCppFile);
        SourceCodeParser parser = new SourceCodeParser(verbose, reader);
        return parser.parseApidocComments(apidoc, matcher, typeManager);
    }
}
