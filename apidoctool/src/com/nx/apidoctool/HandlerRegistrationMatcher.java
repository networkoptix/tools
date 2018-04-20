package com.nx.apidoctool;

import com.nx.util.SourceCode;

import java.util.regex.Pattern;

/**
 * Parses registration for "handler" functions - API functions which are registered in C++ code
 * using a dedicated handler which implements the function.
 */
public final class HandlerRegistrationMatcher implements RegistrationMatcher
{
    /**
     * @return Null if the line is not a registration line.
     */
    public RegistrationMatch createRegistrationMatch(SourceCode sourceCode, int line)
    {
        String[] params;

        params = sourceCode.matchLine(line, regHandlerRegexForFunctor);
        if (params != null)
            return new RegistrationMatch(params[0], null, null, null);

        params = sourceCode.matchLine(line, regHandlerRegexForFunctorInvalidName);
        if (params != null)
            return new RegistrationMatch(null, null, null, null);

        return null;
    }

    //--------------------------------------------------------------------------

    private static final Pattern regHandlerRegexForFunctor = Pattern.compile(
        "\\s*reg\\(\"\\w+\\/([\\w]*)\".*");

    private static final Pattern regHandlerRegexForFunctorInvalidName = Pattern.compile(
        "\\s*reg\\(.*");
}
