package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocUtils;
import com.nx.apidoc.TypeManager;
import com.nx.util.*;
import org.json.JSONObject;

import java.io.File;
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
    public List<Replacement> urlPrefixReplacements;

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

        urlPrefixReplacements = Replacement.parse(params.urlPrefixReplacement());
        int processedFunctionsCount = 0;
        if (!params.templateRegistrationCpp().isEmpty())
        {
            processedFunctionsCount += processCppFile(
                params.templateRegistrationCpp(),
                new TemplateRegistrationMatcher(),
                typeManager);
            processedFunctionsCount += processCppFile(
                params.templateRegistrationCpp(),
                new HandlerRegistrationMatcher(),
                typeManager);
        }
        if (!params.handlerRegistrationCpp().isEmpty())
        {
            processedFunctionsCount += processCppFile(
                params.handlerRegistrationCpp(),
                new HandlerRegistrationMatcher(),
                typeManager);
        }
        for (final String token: params.functionCommentSources().split(","))
        {
            final String source = token.trim();
            if (!source.isEmpty())
            {
                processedFunctionsCount +=
                    processCppFile(source, new FunctionCommentMatcher(), typeManager);
            }
        }

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
                        "    WARNING: Open API schema template is not provided.");
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
        SourceCodeParser parser = new SourceCodeParser(verbose, reader, urlPrefixReplacements);
        return parser.parseApidocComments(apidoc, matcher, typeManager);
    }
}
