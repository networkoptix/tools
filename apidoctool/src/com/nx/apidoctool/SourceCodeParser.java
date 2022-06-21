package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.util.ApiVersion;
import com.nx.util.SourceCode;

import java.util.ArrayList;
import java.util.List;

/**
 * Parses SourceCode to generate Apidoc structure using ApidocCommentParser and ApidocUtils.
 */
public final class SourceCodeParser
{
    private int mainLine;
    private final List<Replacement> urlPrefixReplacements;
    private final List<ApiVersion> apiVersions;

    public final class Error
        extends Exception
    {
        public Error(String message, Throwable cause)
        {
            super(message, cause);
        }

        public Error(String message)
        {
            super(sourceCode.getFilename() + ":" + mainLine + ": " + message);
        }
    }

    public SourceCodeParser(
        boolean verbose,
        boolean unknownParamTypeIsError,
        SourceCode sourceCode,
        List<Replacement> urlPrefixReplacements,
        List<ApiVersion> apiVersions)
    {
        this.verbose = verbose;
        this.unknownParamTypeIsError = unknownParamTypeIsError;
        this.sourceCode = sourceCode;
        this.urlPrefixReplacements = urlPrefixReplacements;
        this.apiVersions = apiVersions;
    }

    public SourceCodeParser(boolean verbose, SourceCode sourceCode)
    {
        this(
            verbose,
            /*unknownParamTypeIsError*/ false,
            sourceCode,
            new ArrayList<Replacement>(),
            new ArrayList<ApiVersion>());
    }

    /**
     * @return Number of API functions processed.
     */
    public int parseApidocComments(
        Apidoc apidoc, RegistrationMatcher matcher, TypeManager typeManager)
        throws
            Error,
            ApidocUtils.Error,
            SourceCode.Error,
            ApidocTagParser.Error,
            ApidocCommentParser.Error,
            TypeManager.Error
    {
        return parseApidocComments(
            apidoc,
            matcher,
            typeManager,
            /*requiredFunctionCaptionLenLimit*/ -1,
            /*requiredGroupNameLenLimit*/ -1);
    }

    /**
     * @return Number of API functions processed.
     */
    public int parseApidocComments(
        Apidoc apidoc,
        RegistrationMatcher matcher,
        TypeManager typeManager,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit)
        throws
            Error,
            ApidocUtils.Error,
            SourceCode.Error,
            ApidocTagParser.Error,
            ApidocCommentParser.Error,
            TypeManager.Error
    {
        if (verbose)
            System.out.println("        Processed API functions:");

        final boolean isApidocWithGroups = !apidoc.groups.isEmpty();
        mainLine = 1;
        int processedFunctionCount = 0;
        while (mainLine <= sourceCode.getLineCount())
        {
            RegistrationMatch match = matcher.createRegistrationMatch(sourceCode, mainLine);
            if (match != null)
            {
                final List<ApidocCommentParser.FunctionDescription> functionDescriptions =
                    createFunctionsFromComment(
                        typeManager,
                        apidoc.groups,
                        urlPrefixReplacements,
                        apiVersions,
                        requiredFunctionCaptionLenLimit,
                        requiredGroupNameLenLimit);
                if (functionDescriptions != null && !functionDescriptions.isEmpty())
                {
                    final String urlPrefix = functionDescriptions.get(0).urlPrefix;
                    for (ApidocCommentParser.FunctionDescription description: functionDescriptions)
                    {
                        if (verbose)
                            System.out.println("            " + description.function.name);

                        if (description.function.groups.isEmpty()
                            && isApidocWithGroups
                            && !urlPrefix.equals(description.urlPrefix))
                        {
                            throw new Error("URL prefix is differ in one apidoc comment: ["
                                + urlPrefix + "] and [" + description.urlPrefix + "]");
                        }

                        checkFunctionProperties(match, description.function);
                        if (typeManager != null)
                        {
                            TypeInfo inputType = description.function.input.type;
                            if (match.inputDataType != null && !match.inputDataType.isEmpty()
                                && inputType.name == null)
                            {
                                try
                                {
                                    inputType.fillFromName(match.inputDataType);
                                }
                                catch (Exception e)
                                {
                                    throw new Error(e.getMessage());
                                }
                                if (inputType.fixed == Apidoc.Type.UUID)
                                {
                                    for (Apidoc.Param param: description.function.input.params)
                                    {
                                        if (param.name.equals("id"))
                                        {
                                            param.type.fixed = Apidoc.Type.UUID;
                                            break;
                                        }
                                    }
                                }
                            }

                            TypeInfo outputType = null;
                            if (description.function.result != null)
                                outputType = description.function.result.type;
                            if (match.outputDataType != null && !match.outputDataType.isEmpty())
                            {
                                if (description.function.result == null)
                                {
                                    description.function.result = new Apidoc.Result();
                                    outputType = description.function.result.type;
                                }
                                if (outputType.name == null)
                                {
                                    try
                                    {
                                        outputType.fillFromName(match.outputDataType);
                                    }
                                    catch (Exception e)
                                    {
                                        throw new Error(e.getMessage());
                                    }
                                }
                            }

                            typeManager.mergeDescription(inputType, outputType, description.function);

                            if (description.function.input.optional)
                            {
                                for (Apidoc.Param param: description.function.input.params)
                                {
                                    if (param.isGeneratedFromStruct)
                                        param.optional = true;
                                }
                            }
                        }

                        if (unknownParamTypeIsError)
                        {
                            for (Apidoc.Param param: description.function.input.params)
                                throwErrorIfUnknownOrUnsupportedParam(description, param, /*isResult*/ false);
                            for (Apidoc.Param param: description.function.result.params)
                                throwErrorIfUnknownOrUnsupportedParam(description, param, /*isResult*/ true);
                        }

                        for (Apidoc.Param param: description.function.input.params)
                            verifyParamValueNames(description, param, /*isResult*/ false);
                        for (Apidoc.Param param: description.function.result.params)
                            verifyParamValueNames(description, param, /*isResult*/ true);

                        if (description.function.groups.isEmpty())
                        {
                            final Apidoc.Group group = ApidocUtils.getGroupByUrlPrefix(
                                apidoc, urlPrefix, description.function.proprietary);
                            if (!ApidocUtils.checkFunctionDuplicate(group, description.function))
                            {
                                throw new Error(
                                    "Duplicate function found: " + description.function.name +
                                        ", method: " + description.function.method);
                            }
                            group.functions.add(description.function);
                        }
                        else
                        {
                            for (final String groupName: description.function.groups)
                            {
                                final Apidoc.Group group = ApidocUtils.getGroupByName(
                                    apidoc, groupName);
                                if (!urlPrefix.isEmpty())
                                {
                                    description.function.name =
                                        urlPrefix.substring(1) + '/' + description.function.name;
                                }
                                if (!ApidocUtils.checkFunctionDuplicate(group, description.function))
                                {
                                    throw new Error(
                                        "Duplicate function found: " + description.function.name +
                                            ", method: " + description.function.method);
                                }
                                group.functions.add(description.function);
                            }
                        }

                        ++processedFunctionCount;
                    }
                }
                else
                {
                    if (verbose && match.functionName != null)
                    {
                        System.out.println("NOTE: " + sourceCode.getFilename() + ":" + mainLine
                            + ": Skipping undocumented function: "
                            + ((match.method == null) ? "" : (match.method + " "))
                            + match.functionName);
                    }
                }
            }
            ++mainLine;
        }
        if (verbose)
            System.out.println("        Functions count: " + processedFunctionCount);

        return processedFunctionCount;
    }

    private void throwErrorIfUnknownOrUnsupportedParam(
        ApidocCommentParser.FunctionDescription description, Apidoc.Param param, boolean isResult)
        throws Error
    {
        if (param.isRef)
            return;
        String error = null;
        switch (param.type.fixed)
        {
            case UNKNOWN:
                error = "unknown type";
                break;
            case OBJECT_JSON:
            case ARRAY_JSON:
            case TEXT:
                error = "unsupported type \"" + param.type.fixed.toString() + "\"";
                break;
            default:
                return;
        }
        throw new Error(description.function.method + " " + description.urlPrefix + "/" +
            description.function.name + ": " + error + " of " + (isResult ? "result " : "") +
            "parameter \"" + param.name + "\".");
    }

    private void verifyParamValueNames(
        ApidocCommentParser.FunctionDescription description, Apidoc.Param param, boolean isResult)
    {
        if (!param.type.fixed.mustBeQuotedInInput() && !param.type.fixed.mustBeUnquotedInInput())
            return;

        for (final Apidoc.Value value: param.values)
        {
            String error = null;
            if (param.type.fixed.mustBeQuotedInInput())
            {
                if (value.areQuotesRemovedFromName)
                    continue;
                error = "must be quoted";
            }
            if (param.type.fixed.mustBeUnquotedInInput())
            {
                if (!value.areQuotesRemovedFromName)
                    continue;
                error = "must be NOT quoted";
            }
            System.out.println("WARNING: " + description.function.method + " " +
                description.urlPrefix + "/" + description.function.name + ": value \"" +
                value.name + "\" of " + (isResult ? "result " : "") + "parameter \"" + param.name +
                "\" " + error + ".");
        }
    }

    //---------------------------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private List<ApidocCommentParser.FunctionDescription> createFunctionsFromComment(
        TypeManager typeManager,
        List<Apidoc.Group> groups,
        List<Replacement> urlPrefixReplacements,
        List<ApiVersion> apiVersions,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit)
        throws ApidocCommentParser.Error, ApidocTagParser.Error, TypeManager.Error
    {
        final List<String> commentLines =
            ApidocTagParser.getPrecedingComment(sourceCode, mainLine - 1);

        if (commentLines == null)
            return null;

        final List<ApidocCommentParser.FunctionDescription> functionDescriptions;
        final int commentStartLine = mainLine - commentLines.size();
        final ApidocCommentParser parser = new ApidocCommentParser();
        functionDescriptions = parser.createFunctionsFromTags(
            ApidocTagParser.getItems(
                commentLines, sourceCode.getFilename(), commentStartLine, verbose),
            typeManager,
            groups,
            urlPrefixReplacements,
            apiVersions,
            requiredFunctionCaptionLenLimit,
            requiredGroupNameLenLimit);

        return functionDescriptions;
    }

    private void checkFunctionProperties(
        RegistrationMatch match, Apidoc.Function function)
        throws Error
    {
        if (match.functionName != null && !function.name.startsWith(match.functionName))
        {
            throw new Error("Function name in Apidoc Comment \"" +
                    function.name +
                    "\" does not match C++ code \"" +
                    match.functionName + "\"");

        }
        if (match.method != null && !function.method.equals(match.method))
        {
            throw new Error("Function method in Apidoc Comment \"" +
                    function.method +
                    "\" does not match C++ code \"" +
                    match.method + "\"");
        }
    }

    //---------------------------------------------------------------------------------------------

    private final boolean verbose;
    private final boolean unknownParamTypeIsError;
    private final SourceCode sourceCode;

    //---------------------------------------------------------------------------------------------
}
