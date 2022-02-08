package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocUtils;
import com.nx.apidoc.TypeManager;
import com.nx.util.*;
import org.json.JSONObject;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

public final class VmsCodeToApiXmlExecutor
    extends Executor
{
    public File vmsPath;
    public File templateApiXmlFile; //< Can be null if not needed.
    public File openApiTemplateJsonFile; //< Can be null if not needed.
    public File outputApiXmlFile; //< Can be null if not needed.
    public File outputApiJsonFile; //< Can be null if not needed.
    public File outputOpenApiJsonFile; //< Can be null if not needed.
    public List<Replacement> urlPrefixReplacements;
    public boolean enableEnumValueMerge = false;

    protected Apidoc apidoc;

    public int execute()
        throws Exception
    {
        System.out.println("apidoctool: parsing apidoc in C++ and inserting into XML");

        if (templateApiXmlFile != null)
        {
            System.out.println("    Input: " + templateApiXmlFile);
        }
        else
        {
            if (outputApiXmlFile != null)
            {
                throw new Exception("\"-output-xml\" parameter requires \"-template-xml\" " +
                    "parameter specified");
            }
            if (outputApiJsonFile != null)
            {
                throw new Exception("\"-output-json\" parameter requires \"-template-xml\" " +
                    "parameter specified");
            }
        }
        if (openApiTemplateJsonFile != null)
            System.out.println("    Input: " + openApiTemplateJsonFile);
        System.out.println("    Input: " + vmsPath + vmsPath.separatorChar);
        if (templateApiXmlFile != null)
        {
            try
            {
                apidoc = XmlSerializer.fromDocument(
                    Apidoc.class, XmlUtils.parseXmlFile(templateApiXmlFile));
                ApidocUtils.checkNoFunctionDuplicates(apidoc);
            }
            catch (Exception e)
            {
                throw new Exception("Error loading API .xml file " + templateApiXmlFile + ": "
                    + e.getMessage());
            }
        }
        else
        {
            apidoc = new Apidoc();

            // Add legacy API predefined groups.
            ApidocUtils.getGroupByName(apidoc, "System API").urlPrefix = "/ec2";
            ApidocUtils.getGroupByName(apidoc, "Proprietary System API").urlPrefix = "/ec2";
            ApidocUtils.getGroupByName(apidoc, "Server API").urlPrefix = "/api";
            ApidocUtils.getGroupByName(apidoc, "Proprietary Server API").urlPrefix = "/api";
        }

        apidoc.enableEnumValueMerge = params.enableEnumValueMerge();

        TypeManager typeManager = null;
        if (!params.typeHeaderPaths().isEmpty())
        {
            List<File> typeHeaders = Utils.getHeaderFileList(vmsPath, params.typeHeaderPaths());
            typeHeaders.sort(
                new Comparator<File>()
                {
                    @Override
                    public int compare(File lhs, File rhs)
                    {
                        return lhs.getName().compareTo(rhs.getName());
                    }
                });
            typeManager = new TypeManager(verbose, params.invalidChronoFieldSuffixIsError(),
                params.unknownParamTypeIsError());
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

        for (final String filename: splitOnTokensSorted(params.handlerRegistrationCpp()))
        {
            processedFunctionsCount +=
                processCppFile(filename, new HandlerRegistrationMatcher(), typeManager);
        }

        for (final String filename: splitOnTokensSorted(params.functionCommentSources()))
        {
            processedFunctionsCount +=
                processCppFile(filename, new FunctionCommentMatcher(), typeManager);
        }

        if (processedFunctionsCount == 0)
            System.out.println("    WARNING: No functions were processed.");
        else
            System.out.println("    API functions processed: " + processedFunctionsCount);

        List<String> groupsToSort = new ArrayList<String>();
        groupsToSort.add("System API");
        groupsToSort.add("Server API");
        groupsToSort.add("Proprietary System API");
        groupsToSort.add("Proprietary Server API");
        ApidocUtils.sortGroups(apidoc, groupsToSort);

        if (outputApiXmlFile != null)
        {
            XmlUtils.writeXmlFile(outputApiXmlFile, XmlSerializer.toDocument(apidoc));
            System.out.println("    Output: " + outputApiXmlFile);
        }

        if (outputApiJsonFile != null)
        {
            final String json = JsonSerializer.toJsonString(apidoc);
            Utils.writeStringToFile(outputApiJsonFile, json);
            System.out.println("    Output: " + outputApiJsonFile);
        }

        if (outputOpenApiJsonFile != null)
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
                json = OpenApiSerializer.toString(
                    apidoc,
                    openApi,
                    params.requiredGroupNameLenLimit(),
                    params.generateOrderByParameters());
            }
            catch (Exception e)
            {
                throw new Exception("Error serializing with Open API template JSON file '"
                        + openApiTemplateJsonFile + "': " + e.getMessage());
            }
            Utils.writeStringToFile(outputOpenApiJsonFile, json);
            System.out.println("    Output: " + outputOpenApiJsonFile);
        }

        return processedFunctionsCount;
    }

    private static List<String> splitOnTokensSorted(final String tokensJoined)
    {
        final List<String> tokens = new ArrayList<String>();
        for (final String token: tokensJoined.split(","))
        {
            final String tokenTrimmed = token.trim();
            if (!tokenTrimmed.isEmpty())
                tokens.add(tokenTrimmed);
        }
        tokens.sort(new Comparator<String>()
        {
            @Override
            public int compare(String lhs, String rhs)
            {
                return lhs.compareTo(rhs);
            }
        });
        return tokens;
    }

    private int processCppFile(
        String sourceCppFilename, RegistrationMatcher matcher, TypeManager typeManager)
        throws Exception
    {
        final File sourceCppFile = new File(vmsPath, sourceCppFilename);
        if (verbose)
            System.out.println("    Parsing API functions from " + sourceCppFile);

        SourceCode reader = new SourceCode(sourceCppFile);
        SourceCodeParser parser = new SourceCodeParser(
            verbose, params.unknownParamTypeIsError(), reader, urlPrefixReplacements);
        return parser.parseApidocComments(apidoc, matcher, typeManager,
            params.requiredFunctionCaptionLenLimit(), params.requiredGroupNameLenLimit());
    }
}
