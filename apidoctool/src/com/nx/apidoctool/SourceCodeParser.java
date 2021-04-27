package com.nx.apidoctool;

import com.nx.apidoc.*;
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
        List<Replacement> urlPrefixReplacements)
    {
        this.verbose = verbose;
        this.unknownParamTypeIsError = unknownParamTypeIsError;
        this.sourceCode = sourceCode;
        this.urlPrefixReplacements = urlPrefixReplacements;
    }

    public SourceCodeParser(boolean verbose, SourceCode sourceCode)
    {
        this(verbose, /*unknownParamTypeIsError*/ false, sourceCode, new ArrayList<Replacement>());
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
                final List<ApidocCommentParser.FunctionDescription> functions =
                    createFunctionsFromComment(
                        typeManager,
                        apidoc.groups,
                        urlPrefixReplacements,
                        requiredFunctionCaptionLenLimit,
                        requiredGroupNameLenLimit);
                if (functions != null && !functions.isEmpty())
                {
                    final String urlPrefix = functions.get(0).urlPrefix;
                    for (ApidocCommentParser.FunctionDescription description: functions)
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
                            String inputStructName = description.inputStructName;
                            if (inputStructName == null)
                                inputStructName = match.inputDataType;

                            String outputStructName = null;
                            if (description.function.result != null)
                                outputStructName = description.function.result.outputStructName;
                            if (outputStructName == null)
                                outputStructName = match.outputDataType;

                            typeManager.mergeDescription(
                                inputStructName, outputStructName, description.function);

                            if (description.inputIsOptional)
                            {
                                for (Apidoc.Param param: description.function.params)
                                {
                                    if (param.isGeneratedFromStruct)
                                        param.optional = true;
                                }
                            }
                        }

                        if (unknownParamTypeIsError)
                        {
                            for (Apidoc.Param param: description.function.params)
                                throwErrorIfUnknownOrUnsupportedParam(description, param, /*isResult*/ false);
                            for (Apidoc.Param param: description.function.result.params)
                                throwErrorIfUnknownOrUnsupportedParam(description, param, /*isResult*/ true);
                        }

                        if (description.function.groups.isEmpty())
                        {
                            final Apidoc.Group group =
                                (requiredGroupNameLenLimit < 0)
                                    ? ApidocUtils.getGroupByUrlPrefix(
                                        apidoc, urlPrefix, description.function.proprietary)
                                    : ApidocUtils.getGroupByName(
                                        apidoc, description.urlPrefix, description.urlPrefix);
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
                                    apidoc, groupName, description.urlPrefix);
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
        switch (param.type)
        {
            case UNKNOWN:
                error = "unknown type";
                break;
            case OBJECT_JSON:
            case ARRAY_JSON:
            case TEXT:
                error = "unsupported type \"" + param.type.toString() + "\"";
                break;
            default:
                return;
        }
        throw new Error(description.function.method + " " + description.urlPrefix + "/" +
            description.function.name + ": " + error + " of " + (isResult ? "result " : "") +
            "parameter \"" + param.name + "\".");
    }

    //---------------------------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private List<ApidocCommentParser.FunctionDescription> createFunctionsFromComment(
        TypeManager typeManager,
        List<Apidoc.Group> groups,
        List<Replacement> urlPrefixReplacements,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit)
        throws ApidocCommentParser.Error, ApidocTagParser.Error, TypeManager.Error
    {
        final List<String> commentLines =
            ApidocTagParser.getPrecedingComment(sourceCode, mainLine - 1);

        if (commentLines == null)
            return null;

        final List<ApidocCommentParser.FunctionDescription> functions;
        final int commentStartLine = mainLine - commentLines.size();
        final ApidocCommentParser parser = new ApidocCommentParser();
        functions = parser.createFunctionsFromTags(
            ApidocTagParser.getItems(
                commentLines, sourceCode.getFilename(), commentStartLine, verbose),
            typeManager,
            groups,
            urlPrefixReplacements,
            requiredFunctionCaptionLenLimit,
            requiredGroupNameLenLimit);

        return functions;
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
