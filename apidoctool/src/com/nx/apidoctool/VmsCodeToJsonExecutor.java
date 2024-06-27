// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.utils.*;
import org.json.JSONObject;

import java.io.File;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public final class VmsCodeToJsonExecutor
    extends Executor
{
    public File vmsPath;
    public File openApiTemplateJsonFile; //< Can be null if not needed.
    public File outputOpenApiJsonFile;

    private List<Replacement> urlPrefixReplacements;
    private List<ApiVersion> apiVersions = new ArrayList<>();
    private Apidoc apidoc;

    public int execute()
        throws Exception
    {
        System.out.println("apidoctool: parsing apidoc in C++ and generating OpenAPI JSON");

        if (openApiTemplateJsonFile != null)
            System.out.println("    Input: " + openApiTemplateJsonFile);
        System.out.println("    Input: " + vmsPath + File.separatorChar);
        apidoc = new Apidoc();

        // Add legacy API predefined groups.
        ApidocUtils.getGroupByName(apidoc, "System API").urlPrefix = "/ec2";
        ApidocUtils.getGroupByName(apidoc, "Proprietary System API").urlPrefix = "/ec2";
        ApidocUtils.getGroupByName(apidoc, "Server API").urlPrefix = "/api";
        ApidocUtils.getGroupByName(apidoc, "Proprietary Server API").urlPrefix = "/api";

        apidoc.enableEnumValueMerge = params.enableEnumValueMerge();

        TypeManager typeManager = null;
        if (!params.typeHeaderPaths().isEmpty())
        {
            List<File> typeHeaders = Utils.getHeaderFileList(vmsPath, params.typeHeaderPaths());
            Collections.sort(typeHeaders,
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
        for (final String value: Utils.splitOnTokensTrimmed(params.apiVersions()))
            apiVersions.add(new ApiVersion(value));

        int processedFunctionsCount = 0;
        if (!params.templateRegistrationCpp().isEmpty())
        {
            processedFunctionsCount += processCppFileFunctions(
                params.templateRegistrationCpp(),
                new TemplateRegistrationMatcher(),
                typeManager);
            processedFunctionsCount += processCppFileFunctions(
                params.templateRegistrationCpp(),
                new HandlerRegistrationMatcher(),
                typeManager);
        }

        for (final String filename: Utils.splitOnTokensTrimmed(params.handlerRegistrationCpp()))
        {
            processedFunctionsCount +=
                processCppFileFunctions(filename, new HandlerRegistrationMatcher(), typeManager);
        }

        for (final String filename: Utils.splitOnTokensTrimmed(params.functionCommentSources()))
        {
            processedFunctionsCount +=
                processCppFileFunctions(filename, new FunctionCommentMatcher(), typeManager);
        }

        for (final String filename: Utils.splitOnTokensTrimmed(params.transactionBusSources()))
        {
            processedFunctionsCount +=
                processCppFileTransactions(filename, new TransactionBusMatcher(), typeManager);
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
                    System.out.println("    WARNING: Open API schema template is not provided.");
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
                json = ApiVersion.applyExactVersion(
                    OpenApiSerializer.toString(
                        apidoc,
                        openApi,
                        params.requiredGroupNameLenLimit(),
                        params.generateOrderByParameters()),
                    apiVersions);
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

    private int processCppFileFunctions(
        String sourceCppFilename, RegistrationMatcher matcher, TypeManager typeManager)
        throws Exception
    {
        final File sourceCppFile = new File(vmsPath, sourceCppFilename);
        if (verbose)
            System.out.println("    Parsing API functions from " + sourceCppFile);

        SourceCode reader = new SourceCode(sourceCppFile);
        SourceCodeParser parser = new SourceCodeParser(
            verbose,
            params.unknownParamTypeIsError(),
            reader,
            urlPrefixReplacements,
            apiVersions);
        return parser.parseApidocComments(
            apidoc,
            matcher,
            typeManager,
            params.requiredFunctionCaptionLenLimit(),
            params.requiredGroupNameLenLimit(),
            params.responseChronoAsString(),
            /*isTransactionBus*/ false);
    }

    private int processCppFileTransactions(
        String sourceCppFilename, RegistrationMatcher matcher, TypeManager typeManager)
        throws Exception
    {
        final File sourceCppFile = new File(vmsPath, sourceCppFilename);
        if (verbose)
            System.out.println("    Parsing Transactions from " + sourceCppFile);

        SourceCode reader = new SourceCode(sourceCppFile);
        SourceCodeParser parser = new SourceCodeParser(
            verbose,
            params.unknownParamTypeIsError(),
            reader,
            urlPrefixReplacements,
            apiVersions);
        return parser.parseApidocComments(
            apidoc,
            matcher,
            typeManager,
            params.requiredFunctionCaptionLenLimit(),
            params.requiredGroupNameLenLimit(),
            params.responseChronoAsString(),
            /*isTransactionBus*/ true);
    }
}
