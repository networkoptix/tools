package com.nx.apidoctool;

import com.nx.util.SourceCode;

import java.util.regex.Pattern;

/**
 * Parses source comments for multiline apidoc method comments.
 */
public final class MethodCommentMatcher implements RegistrationMatcher
{
    /**
     * @return Null if the line is not an end of a multiline apidoc method comment.
     */
    public RegistrationMatch createRegistrationMatch(SourceCode sourceCode, int line)
        throws SourceCode.Error
    {
        assert line > 0;
        assert line <= sourceCode.getLineCount();

        int index = line;
        String text = sourceCode.getLine(index);
        if (!firstLineRegex.matcher(text).matches())
            return null;

        ++index;
        while (index <= sourceCode.getLineCount())
        {
            text = text + " " + sourceCode.getLine(index);
            if (lastLineRegex.matcher(sourceCode.getLine(index)).matches())
            {
                final RegistrationMatch match = new RegistrationMatch(null, null, null, null);
                match.mainLineCorrection = index - line + 1;
                return match;
            }
            ++index;
        }
        return null;
    }

    private static final Pattern firstLineRegex = Pattern.compile(
        "\\s*/\\*\\*%apidoc (GET|POST|PUT|PATCH|DELETE).*");

    private static final Pattern lastLineRegex = Pattern.compile("\\s*\\*/\\s*");
}
