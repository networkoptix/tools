package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocCommentParser;
import com.nx.apidoc.ApidocTagParser;
import com.nx.apidoc.ApidocUtils;
import com.nx.util.SourceCode;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Parses SourceCode to generate Apidoc structure using ApidocCommentParser and ApidocUtils.
 */
public final class SourceCodeParser
{
    private int mainLine;

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
    }

    public SourceCode getSourceCode()
    {
        return sourceCode;
    }

    /**
     * @return Number of API functions processed.
     */
    public int parseApidocComments(Apidoc apidoc, RegistrationMatcher matcher)
        throws Error, ApidocUtils.Error, SourceCode.Error
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
                final List<ApidocCommentParser.FunctionDescription> functions =
                    createFunctionsFromComment();
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
            }
            ++mainLine;
        }
        if (verbose)
            System.out.println("        Functions count: " + processedFunctionCount);

        return processedFunctionCount;
    }

    //--------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private List<ApidocCommentParser.FunctionDescription> createFunctionsFromComment()
        throws Error
    {
        // Look for an Apidoc Comment end "*/" directly above the main line.
        int line = mainLine - 1;
        if (line == 0 || !sourceCode.lineMatches(line, commentEndRegex))
            return null;

        --line;
        // Now line points to the line preceding the comment-end line "*/".

        while (line > 0 && !sourceCode.lineMatches(line, commentStartRegex))
            --line;
        if (line == 0) //< Did not find comment start.
            return null;

        // Now line points to a comment start: "/*...".

        // Check that the found comment starts with "/**".
        if (!sourceCode.lineMatches(line, apidocCommentStartRegex))
            return null;

        List<String> commentLines = new ArrayList<String>(mainLine - line);
        for (int i = line; i < mainLine - 1; ++i)
            commentLines.add(sourceCode.getLine(i));

        final List<ApidocCommentParser.FunctionDescription> functions;
        try
        {
            final ApidocCommentParser parser = new ApidocCommentParser();
            final ApidocTagParser tagParser = new ApidocTagParser(
                commentLines, sourceCode.getFilename(), line, verbose);
            functions = parser.createFunctionsFromCommentLines(tagParser);
        }
        catch (ApidocCommentParser.Error e)
        {
            throw new Error(e.getMessage());
        }
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

    //--------------------------------------------------------------------------

    private final boolean verbose;
    private final SourceCode sourceCode;

    //--------------------------------------------------------------------------

    private static final Pattern commentEndRegex = Pattern.compile(
        "\\s*\\*/\\s*");

    private static final Pattern commentStartRegex = Pattern.compile(
        "\\s*/\\*.*");

    private static final Pattern apidocCommentStartRegex = Pattern.compile(
        "\\s*/\\*\\*.*");
}
