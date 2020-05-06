package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocUtils;
import com.nx.apidoc.TypeManager;
import com.nx.util.*;
import org.json.JSONObject;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

public final class VmsCodeToApiXmlExecutor
    extends Executor
{
    public File vmsPath;
    public File templateApiXmlFile;
    public File openApiTemplateJsonFile;
    public File outputApiXmlFile;
    public File optionalOutputApiJsonFile; //< Can be null if not needed.
    public File optionalOutputOpenApiJsonFile; //< Can be null if not needed.
    public String urlPrefixReplacement = "";

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

        urlPrefixReplacement = params.urlPrefixReplacement();
        int processedFunctionsCount = 0;
        final RegistrationMatcher matcher = new HandlerRegistrationMatcher();
        if (!params.templateRegistrationCpp().isEmpty())
        {
            processedFunctionsCount += processCppFile(
                params.templateRegistrationCpp(),
                new TemplateRegistrationMatcher(),
                typeManager);
            processedFunctionsCount += processCppFile(
                params.templateRegistrationCpp(),
                matcher,
                typeManager);
        }
        for (final String token: params.handlerRegistrationCpp().split(","))
            processedFunctionsCount += processCppFile(token.trim(), matcher, typeManager);

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
            JSONObject openApi;
            try
            {
                if (openApiTemplateJsonFile != null)
                {
                    openApi = new JSONObject(
                        new String(Files.readAllBytes(openApiTemplateJsonFile.toPath())));
                }
                else
                {
                    openApi = new JSONObject();
                    System.out.println(
                            "    WARNING: Open API schema template is not provided");
                }
            }
            catch (Exception e)
            {
                throw new Exception("Error loading Open API template JSON file '"
                    + openApiTemplateJsonFile + "': " + e.getMessage());
            }
            String json;
            try
            {
                json = OpenApiSerializer.toString(apidoc, openApi);
            }
            catch (Exception e)
            {
                throw new Exception("Error serializing with Open API template JSON file '"
                        + openApiTemplateJsonFile + "': " + e.getMessage());
            }
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
        SourceCodeParser parser = new SourceCodeParser(verbose, reader, urlPrefixReplacement);
        return parser.parseApidocComments(apidoc, matcher, typeManager);
    }
}
