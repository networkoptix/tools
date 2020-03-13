package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.util.SourceCode;
import com.nx.util.SourceCodeEditor;
import com.nx.util.Utils;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Parses SourceCode to generate Apidoc structure using ApidocCommentParser and ApidocUtils.
 */
public final class SourceCodeParser
{
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

    public SourceCodeParser(boolean verbose, SourceCode sourceCode)
    {
        this.verbose = verbose;
        this.sourceCode = sourceCode;

        try
        {
            this.generatedCommentsSourceCodeEditor = new SourceCodeEditor(new File(sourceCode.getFilename()));
        }
        catch (IOException e)
        {
            this.generatedCommentsSourceCodeEditor = null; //< Warning suppress.
            System.err.println("ERROR: Unable to create generated comments file: " + e.getMessage());
        }
    }

    /**
     * @return Number of API functions processed.
     */
    public int parseApidocComments(
        Apidoc apidoc, List<RegistrationMatcher> matchers, TypeManager typeManager)
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
            for (RegistrationMatcher matcher: matchers)
            {
                RegistrationMatch match = matcher.createRegistrationMatch(sourceCode, mainLine);
                if (match != null)
                {
                    final List<ApidocCommentParser.FunctionDescription> functions =
                        createFunctionsFromComment(typeManager);
                    if (functions != null && !functions.isEmpty())
                    {
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

                            if (generatedCommentsSourceCodeEditor != null)
                                generateCommentForUndocumentedFunction(match);
                        }
                    }
                }
            }
            ++mainLine;
        }
        if (verbose)
            System.out.println("        Functions count: " + processedFunctionCount);

        if (generatedCommentsSourceCodeEditor != null)
            saveGeneratedCommentsFile();

        return processedFunctionCount;
    }

    private void saveGeneratedCommentsFile()
    {
        final File generatedCommentsFile = Utils.insertSuffix(new File(sourceCode.getFilename()), ".with_undoc_stubs");

        try
        {
            generatedCommentsSourceCodeEditor.saveToFile(generatedCommentsFile);
            System.out.println("ATTENTION: Generated file with stubs comments: "
                + generatedCommentsFile.getAbsolutePath());
        }
        catch (IOException e)
        {
            System.err.println("ERROR: Unable to save generated comments file "
                + generatedCommentsFile.getAbsolutePath() + ": " + e.getMessage());
        }
    }

    private void generateCommentForUndocumentedFunction(RegistrationMatch registrationMatch)
    {
        final List<String> comment = new ArrayList<String>();
        final String method = (registrationMatch.method == null) ? "TODO" : registrationMatch.method;
        final String urlPrefix = (registrationMatch.urlPrefix == null) ? "TODO/" : registrationMatch.urlPrefix;
        comment.add("/**%apidoc[proprietary] " + method  + " /" + urlPrefix + registrationMatch.functionName);
        comment.add(" * %// TODO: Write apidoc comment.");

        int lineBeforeReg = mainLine - 1;

        // If the line before the reg line is a "//"-comment, include it into apidoc as "%//".
        if (mainLine > 1 && sourceCode.getLine(mainLine - 1).trim().startsWith("//"))
        {
            final String sourceCodeCommentBody =
                sourceCode.getLine(mainLine - 1).trim().substring("//".length()).trim();
            generatedCommentsSourceCodeEditor.deleteLine(generatedCommentsInsertedLinesCount + mainLine - 1);
            --generatedCommentsInsertedLinesCount;
            --lineBeforeReg;
            comment.add(" * %// " + sourceCodeCommentBody);
        }

        // If there was no empty line before the function registration, insert it before the new comment.
        if (lineBeforeReg > 0 && !sourceCode.getLine(lineBeforeReg).trim().isEmpty())
            comment.add(0, "");

        comment.add(" */");

        Utils.indentStrings(comment, Utils.determineIndent(sourceCode.getLine(mainLine)));

        final int lineToInsertBefore = mainLine + generatedCommentsInsertedLinesCount;
        final int insertedLineCount = generatedCommentsSourceCodeEditor.insertLines(lineToInsertBefore, comment);
        generatedCommentsInsertedLinesCount += insertedLineCount;
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

    private int mainLine;

    private SourceCodeEditor generatedCommentsSourceCodeEditor;
    private int generatedCommentsInsertedLinesCount;
}
