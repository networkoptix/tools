package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocCommentParser;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.SourceCode;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Parses SourceCode to generate Apidoc structure using ApidocCommentParser and ApidocHandler.
 */
public final class SourceCodeParser
{
    public static final class Error
        extends Exception
    {
        public Error(String message, Throwable cause)
        {
            super(message, cause);
        }

        public Error(String message)
        {
            super(message);
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
    public int parseCommentsFromSystemApi(
        Apidoc.Group sourceGroup, Apidoc.Group targetGroup)
        throws Error, ApidocHandler.Error, ApidocCommentParser.Error, SourceCode.Error
    {
        targetGroup.groupName = sourceGroup.groupName;
        targetGroup.urlPrefix = sourceGroup.urlPrefix;
        targetGroup.groupDescription = sourceGroup.groupDescription;

        int line = 1;
        while (line <= sourceCode.getLineCount())
        {
            MatchForRegisterHandler match = MatchForRegisterHandler.create(sourceCode, line);
            if (match != null)
            {
                Apidoc.Function function = createFunctionFromComment(
                    match, line, targetGroup.urlPrefix);
                if (function != null)
                {
                    if (verbose)
                    {
                        if (targetGroup.functions.isEmpty())
                            System.out.println("    Processed API functions:");
                        System.out.println("        " + function.name);
                    }
                    targetGroup.functions.add(function);
                }
            }

            ++line;
        }

        if (targetGroup.functions.isEmpty())
            System.out.println("    WARNING: No functions were processed.");

        return targetGroup.functions.size();
    }

    //--------------------------------------------------------------------------

    /**
     * @param mainLine Line of code below the Apidoc Comment.
     * @return Null if the comment should not convert to an XML function.
     */
    private Apidoc.Function createFunctionFromComment(
        MatchForRegisterHandler match, int mainLine, String expectedUrlPrefix)
        throws Error, ApidocCommentParser.Error
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

        final Apidoc.Function function =
            ApidocCommentParser.createFunctionFromCommentLines(
                commentLines, expectedUrlPrefix, match.functionName);

        checkFunctionProperties(match, function);

        return function;
    }

    private static void checkFunctionProperties(
        MatchForRegisterHandler match, Apidoc.Function function)
        throws Error
    {
        if (function != null)
        {
            if (!function.name.equals(match.functionName))
            {
                throw new Error("Function name in Apidoc Comment \"" +
                    function.name +
                    "\" does not match C++ code \"" +
                    match.functionName + "\"");

            }
            if (!function.method.equals(match.method))
            {
                throw new Error("Function method in Apidoc Comment \"" +
                    function.method +
                    "\" does not match C++ code \"" +
                    match.method + "\"");
            }
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
