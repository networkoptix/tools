package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocCommentParser;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.SourceCode;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Parses SourceCode to generate Apidoc structure using ApidocCommentParser and
 * ApidocHandler.
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

    public SourceCodeParser(SourceCode sourceCode)
    {
        this.sourceCode = sourceCode;
    }

    public SourceCode getSourceCode()
    {
        return sourceCode;
    }

    public Apidoc.Group parseCommentsFromSystemApi(Apidoc.Group group)
        throws Error, ApidocHandler.Error, ApidocCommentParser.Error,
        SourceCode.Error
    {
        final Apidoc.Group targetGroup = new Apidoc.Group();
        targetGroup.groupName = group.groupName;
        targetGroup.urlPrefix = group.urlPrefix;
        targetGroup.groupDescription = group.groupDescription;

        int line = 1;
        while (line < sourceCode.getLineCount())
        {
            MatchForRegisterHandler match = MatchForRegisterHandler.create(
                sourceCode, line);
            if (match != null)
            {
                Apidoc.Function function = createFunctionFromComment(
                    match, line, targetGroup.urlPrefix);
                if (function != null)
                {
                    System.out.println("Processed function: " + function.name);
                    targetGroup.functions.add(function);
                }
            }

            ++line;
        }

        return targetGroup;
    }

    //--------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private Apidoc.Function createFunctionFromComment(
        MatchForRegisterHandler match, int mainLine, String expectedUrlPrefix)
        throws Error, ApidocCommentParser.Error
    {
        // Look for an Apidoc Comment above the main line.
        int line = mainLine - 1;
        if (line == 0 ||
            !sourceCode.lineMatches(line, commentEndRegex))
        {
            return null;
        }

        --line; //< line points to the line preceding comment end line.
        while (line > 0 &&
            !sourceCode.lineMatches(line, commentStartRegex))
        {
            --line;
        }
        if (line == 0) //< Did not find Apidoc Comment start.
            return null;

        // line points to Apidoc Comment start.

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

    private SourceCode sourceCode;

    //--------------------------------------------------------------------------

    private static final Pattern commentEndRegex = Pattern.compile(
        "\\s*\\*/\\s*");

    private static final Pattern commentStartRegex = Pattern.compile(
        "\\s*/\\*\\*.*");
}
