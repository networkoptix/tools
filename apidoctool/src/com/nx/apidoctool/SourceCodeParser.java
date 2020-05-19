package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.util.SourceCode;
import javafx.util.Pair;

import java.util.ArrayList;
import java.util.List;

/**
 * Parses SourceCode to generate Apidoc structure using ApidocCommentParser and ApidocUtils.
 */
public final class SourceCodeParser
{
    private int mainLine;
    private ArrayList<Pair<String, String>> replacements = new ArrayList<Pair<String, String>>();

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

    public SourceCodeParser(boolean verbose, SourceCode sourceCode, String urlPrefixReplacements)
    {
        this.verbose = verbose;
        this.sourceCode = sourceCode;
        if (urlPrefixReplacements.isEmpty())
            return;
        for (final String replacement: urlPrefixReplacements.split(","))
        {
            final String[] pair = replacement.split(":");
            if (pair.length != 2)
            {
                throw new IllegalArgumentException(
                    "Invalid urlPrefixReplacements parameter, see help for valid format.");
            }
            final String target = pair[0].trim();
            final String replace = pair[1].trim();
            if (target.isEmpty() || replace.isEmpty())
            {
                throw new IllegalArgumentException(
                    "Invalid urlPrefixReplacements parameter, see help for valid format.");
            }
            replacements.add(new Pair<String, String>(target, replace));
        }
    }

    /**
     * @return Number of API functions processed.
     */
    public int parseApidocComments(
        Apidoc apidoc, RegistrationMatcher matcher, TypeManager typeManager)
        throws Error,
        ApidocUtils.Error,
        SourceCode.Error,
        ApidocTagParser.Error,
        ApidocCommentParser.Error,
        TypeManager.Error
    {
        if (verbose)
            System.out.println("        Processed API functions:");

        mainLine = 1;
        int processedFunctionCount = 0;
        while (mainLine <= sourceCode.getLineCount())
        {
            RegistrationMatch match = matcher.createRegistrationMatch(sourceCode, mainLine);
            if (match != null)
            {
                mainLine += match.mainLineCorrection;
                final List<ApidocCommentParser.FunctionDescription> functions =
                    createFunctionsFromComment(typeManager);
                if (functions != null && !functions.isEmpty())
                {
                    for (ApidocCommentParser.FunctionDescription description: functions)
                    {
                        for (Pair<String, String> replacement: replacements)
                        {
                            description.urlPrefix = description.urlPrefix.replace(
                                replacement.getKey(), replacement.getValue());
                        }
                    }
                    final String urlPrefix = functions.get(0).urlPrefix;
                    final Apidoc.Group group = ApidocUtils.getGroupByUrlPrefix(apidoc, urlPrefix);

                    for (ApidocCommentParser.FunctionDescription description: functions)
                    {
                        if (!urlPrefix.equals(description.urlPrefix))
                        {
                            throw new Error("URL prefix is differ in one apidoc comment: ["
                                + urlPrefix + "] and [" + description.urlPrefix + "]");
                        }
                        if (verbose)
                            System.out.println("            " + description.function.name);

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
                                    if (param.isGeneratedFromStruct &&
                                        param.structName.equals(inputStructName))
                                    {
                                        param.optional = true;
                                    }
                                }
                            }
                        }

                        if (!ApidocUtils.checkFunctionDuplicate(group, description.function))
                        {
                            throw new Error(
                                "Duplicate function found: " + description.function.name +
                                ", method: " + description.function.method);
                        }

                        ++processedFunctionCount;
                        group.functions.add(description.function);
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

    //---------------------------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private List<ApidocCommentParser.FunctionDescription> createFunctionsFromComment(
        TypeManager typeManager)
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
            typeManager);

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
    private final SourceCode sourceCode;

    //---------------------------------------------------------------------------------------------
}
