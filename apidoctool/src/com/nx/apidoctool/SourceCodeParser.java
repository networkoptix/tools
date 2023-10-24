// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.apidoc.ApiVersion;
import com.nx.utils.SourceCode;

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
        Apidoc apidoc,
        RegistrationMatcher matcher,
        TypeManager typeManager,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit,
        boolean responseChronoAsString,
        boolean isTransactionBus)
        throws
            Error,
            ApidocUtils.Error,
            SourceCode.Error,
            ApidocTagParser.Error,
            ApidocCommentParser.Error,
            TypeManager.Error
    {
        if (verbose)
        {
            System.out.println("        Processed " +
                (isTransactionBus ? "Transactions" : "API functions") + ":");
        }

        final boolean hasApidocLegacyGroups = !apidoc.groups.isEmpty();
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
                        requiredFunctionCaptionLenLimit,
                        requiredGroupNameLenLimit,
                        isTransactionBus
                            ? ApidocCommentParser.FunctionType.TRANSACTION
                            : ApidocCommentParser.FunctionType.API);
                if (functionDescriptions != null && !functionDescriptions.isEmpty())
                {
                    final String initialUrlPrefix = functionDescriptions.get(0).urlPrefix;
                    for (ApidocCommentParser.FunctionDescription description: functionDescriptions)
                    {
                        processFunctionDescription(
                            apidoc,
                            typeManager,
                            responseChronoAsString,
                            hasApidocLegacyGroups,
                            match,
                            initialUrlPrefix,
                            description);

                        ++processedFunctionCount;
                    }
                }
                else
                {
                    if (verbose && match.functionName != null && !isTransactionBus)
                    {
                        System.out.println("WARNING: " + sourceCode.getFilename() + ":" + mainLine
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

    private void processFunctionDescription(
        Apidoc apidoc,
        TypeManager typeManager,
        boolean responseChronoAsString,
        boolean hasApidocLegacyGroups,
        RegistrationMatch match,
        String initialUrlPrefix,
        ApidocCommentParser.FunctionDescription description)
        throws
            Error,
            TypeManager.Error,
            ApidocUtils.Error
    {
        if (description.function.method == null)
            description.function.method = match.method;
        if (description.function.name == null)
            description.function.name = match.functionName;

        if (verbose)
        {
            System.out.println(
                "            " + description.function.method + " " + description.function.name);
        }

        if (description.function.groups.isEmpty()
            && hasApidocLegacyGroups
            && !initialUrlPrefix.equals(description.urlPrefix))
        {
            throw new Error("URL prefix differs in one apidoc comment: ["
                + initialUrlPrefix + "] and [" + description.urlPrefix + "]");
        }

        if (!hasApidocLegacyGroups)
            checkFunctionProperties(match, description.function);
        if (typeManager != null)
            processFunctionTypes(typeManager, match, description);

        if (unknownParamTypeIsError)
        {
            for (Apidoc.Param param: description.function.input.params)
                throwErrorIfUnknownOrUnsupportedParam(description, param, /*isResult*/ false);
            for (Apidoc.Param param: description.function.result.params)
                throwErrorIfUnknownOrUnsupportedParam(description, param, /*isResult*/ true);
        }

        for (Apidoc.Param param: description.function.input.params)
            throwErrorIfExampleTypeInvalid(description, param, /*isResult*/ false);
        for (Apidoc.Param param: description.function.result.params)
            throwErrorIfExampleTypeInvalid(description, param, /*isResult*/ true);
        throwErrorIfExampleTypeInvalid(description, description.function.input, /*isResult*/ false);
        throwErrorIfExampleTypeInvalid(description, description.function.result, /*isResult*/ true);

        if (verbose)
        {
            for (Apidoc.Param param: description.function.input.params)
                verifyParamValueNames(description, param, /*isResult*/ false);
            for (Apidoc.Param param: description.function.result.params)
                verifyParamValueNames(description, param, /*isResult*/ true);
        }
        for (Apidoc.Param param: description.function.result.params)
            param.type.setFixedChrono(responseChronoAsString);

        if (description.function.groups.isEmpty())
        {
            final Apidoc.Group group = initialUrlPrefix.isEmpty()
                ? ApidocUtils.getGroupByName(apidoc, /*groupName*/ "")
                : ApidocUtils.getGroupByUrlPrefix(
                    apidoc, initialUrlPrefix, description.function.proprietary);
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
                if (!initialUrlPrefix.isEmpty())
                {
                    description.function.name =
                        initialUrlPrefix.substring(1) + '/' + description.function.name;
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
    }

    private void processFunctionTypes(
        TypeManager typeManager,
        RegistrationMatch match,
        ApidocCommentParser.FunctionDescription description)
        throws
            Error,
            TypeManager.Error
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

    private void throwErrorIfUnknownOrUnsupportedParam(
        ApidocCommentParser.FunctionDescription description, Apidoc.Param param, boolean isResult)
        throws Error
    {
        if (param.isRef)
            return;
        String error = null;
        if (param.type.mapValueType == null && param.type.variantValueTypes == null)
        {
            if (param.type.fixed != Apidoc.Type.UNKNOWN)
                return;
            error = "unknown type";
        }
        else if (param.type.mapValueType != null)
        {
            if (param.type.mapValueType.fixed != Apidoc.Type.UNKNOWN)
                return;
            error = "unknown map value type";
        }
        else if (param.type.variantValueTypes != null)
        {
            for (final TypeInfo variantType: param.type.variantValueTypes)
            {
                if (variantType.fixed == Apidoc.Type.UNKNOWN)
                {
                    error = "unknown variant value type `" + variantType.name + "`";
                    break;
                }
            }
            if (error == null)
                return;
        }
        throw new Error(description.function.method + " " + description.urlPrefix + "/" +
            description.function.name + ": " + error + " of " + (isResult ? "result " : "") +
            "parameter \"" + param.name + "\".");
    }

    private void throwErrorIfExampleTypeInvalid(
        ApidocCommentParser.FunctionDescription description, Apidoc.InOutData data, boolean isResult)
        throws Error
    {
        if (data.example.isEmpty())
            return;
        try
        {
            data.type.parse(data.example);
        }
        catch (Throwable e)
        {
            throw new Error(description.function.method + " " + description.urlPrefix + "/" +
                description.function.name + ": " + (isResult ? "result " : "") + "\" \"%example " +
                data.example + "\" type is invalid.");
        }
    }

    private void throwErrorIfExampleTypeInvalid(
        ApidocCommentParser.FunctionDescription description, Apidoc.Param param, boolean isResult)
        throws Error
    {
        String error = null;
        if (!param.example.isEmpty())
        {
            try
            {
                param.type.parse(param.example);
            }
            catch (Throwable e)
            {
                error = "\"%example " + param.example + "\" type is invalid.";
            }
        }
        if (error == null)
        {
            if (!param.needExample())
                return;

            for (final Apidoc.Value value: param.values)
            {
                if (value.deprecated || value.proprietary || value.unused)
                    continue;

                try
                {
                    param.type.parse(value.name);
                    break;
                }
                catch (Throwable e)
                {
                    error = "\"%value " + value.name + "\" type is invalid.";
                }
            }
        }
        if (error == null)
            return;

        throw new Error(description.function.method + " " + description.urlPrefix + "/" +
            description.function.name + ": " + (isResult ? "result " : "") + "parameter \"" +
            param.name + "\" " + error);
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
     * @return Null if the comment should not convert to a Function.
     */
    private List<ApidocCommentParser.FunctionDescription> createFunctionsFromComment(
        TypeManager typeManager,
        List<Apidoc.Group> groups,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit,
        ApidocCommentParser.FunctionType functionType)
        throws ApidocCommentParser.Error, ApidocTagParser.Error, TypeManager.Error
    {
        final List<String> commentLines =
            ApidocTagParser.getPrecedingComment(sourceCode, mainLine - 1);

        if (commentLines == null)
            return null;

        final List<ApidocCommentParser.FunctionDescription> functionDescriptions;
        final int commentStartLine = mainLine - commentLines.size();
        final ApidocCommentParser apidocCommentParser = new ApidocCommentParser();
        functionDescriptions = apidocCommentParser.createFunctionsFromTags(
            ApidocTagParser.getItems(
                commentLines, sourceCode.getFilename(), commentStartLine, verbose),
            typeManager,
            groups,
            urlPrefixReplacements,
            apiVersions,
            requiredFunctionCaptionLenLimit,
            requiredGroupNameLenLimit,
            functionType);

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
}
