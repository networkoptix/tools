// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.utils.SourceCode;

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

        params = sourceCode.matchLine(line, regHandlerRegexForFunctorWithSpecialName);
        if (params != null)
            return new RegistrationMatch(null, null, null, null);

        params = sourceCode.matchLine(line, regHandlerRegexForFunctorWithInvalidName);
        if (params != null)
            return new RegistrationMatch(null, null, null, null);

        return null;
    }

    //---------------------------------------------------------------------------------------------

    private static final Pattern regHandlerRegexForFunctor = Pattern.compile(
        "\\s*reg\\(\"\\w+\\/([\\w-]*\\/?)\".*");

    /**
     * Allow a function registration with a name that is defined as a non-literal string or a
     * string literal with the special symbols (*:?). Such name is not intended to match its
     * function name in the apidoc comment.
     */
    private static final Pattern regHandlerRegexForFunctorWithSpecialName = Pattern.compile(
        "\\s*reg\\((?:[^\"]|\"[\\w\\?\\:\\*\\/]+\").*");

    private static final Pattern regHandlerRegexForFunctorWithInvalidName = Pattern.compile(
        "\\s*reg\\(.*");
}
