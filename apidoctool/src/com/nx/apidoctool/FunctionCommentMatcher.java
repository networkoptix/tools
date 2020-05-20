package com.nx.apidoctool;

import com.nx.util.SourceCode;

import java.util.regex.Pattern;

/**
 * Parses source comments for multiline apidoc API function comments.
 */
public final class FunctionCommentMatcher implements RegistrationMatcher
{
    /**
     * @return Null if line is not a next line after a multiline apidoc API function comment end.
     */
    public RegistrationMatch createRegistrationMatch(SourceCode sourceCode, int line)
    {
        assert line == previousLine + 1;
        previousLine = line;
        if (isLastLineFound)
        {
            firstLine = 0;
            isLastLineFound = false;
            return new RegistrationMatch(null, null, null, null);
        }
        if (firstLine == 0)
        {
            if (firstLineRegex.matcher(sourceCode.getLine(line)).matches())
                firstLine = line;
        }
        else
        {
            isLastLineFound = lastLineRegex.matcher(sourceCode.getLine(line)).matches();
        }
        return null;
    }

    private int previousLine = 0;
    private int firstLine = 0;
    private boolean isLastLineFound = false;

    private static final Pattern firstLineRegex = Pattern.compile(
        "\\s*/\\*\\*%apidoc (GET|POST|PUT|PATCH|DELETE).*");

    private static final Pattern lastLineRegex = Pattern.compile("\\s*\\*/\\s*");
}
