// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.utils.SourceCode;

import java.util.regex.Pattern;

/**
 * Parses registration for "template" functions - API functions which are registered in C++ code
 * using a C++ template function with input and output data types as template parameters.
 */
public final class TemplateRegistrationMatcher implements RegistrationMatcher
{
    /**
     * @return Null if the line is not a registration line.
     */
    public RegistrationMatch createRegistrationMatch(SourceCode sourceCode, int line)
        throws SourceCode.Error
    {
        String[] params;

        params = sourceCode.matchMultiline(
            line, firstLineRegexForGetFunc, groupRegexForGetFunc, lastLineRegex);
        if (params != null)
            return createMatch(params[2], params[0], params[1], "GET");

        params = sourceCode.matchMultiline(
            line, firstLineRegexForUpdateFunc, groupRegexForUpdateFunc, lastLineRegex);
        if (params != null)
            return createMatch(params[1], params[0], "", "POST");

        params = sourceCode.matchMultiline(
            line, firstLineRegexForFunctor, groupRegexForFunctor, lastLineRegex);
        if (params != null)
            return createMatch(params[2], params[0], params[1], "GET");

        return null;
    }

    //---------------------------------------------------------------------------------------------

    private static RegistrationMatch createMatch(
        String functionName,
        String inputDataType,
        String outputDataType,
        String method)
    {
        assert functionName != null;
        assert !functionName.isEmpty();
        assert inputDataType != null;
        assert outputDataType != null;
        assert method != null;
        assert !method.isEmpty();

        if ("std::nullptr_t".equals(inputDataType))
            inputDataType = null;

        return new RegistrationMatch(functionName, inputDataType, outputDataType, method);
    }

    //---------------------------------------------------------------------------------------------

    private static final Pattern lastLineRegex = Pattern.compile(
        ".*[;\\[].*");

    private static final Pattern firstLineRegexForGetFunc = Pattern.compile(
        "\\s*reg\\w*Get\\w*\\s*<.*");

    private static final Pattern groupRegexForGetFunc = Pattern.compile(
        "\\s*reg\\w*Get\\w*\\s*<\\s*" +
        "([a-zA-Z_0-9:]+)" +
        "\\s*,\\s*" +
        "(\\w+)" +
        "\\s*>.+ApiCommand\\s*::\\s*(\\w+).*");

    private static final Pattern firstLineRegexForUpdateFunc = Pattern.compile(
        "\\s*reg\\w*Update\\w*\\s*<.*");

    private static final Pattern groupRegexForUpdateFunc = Pattern.compile(
        "\\s*reg\\w*Update\\w*\\s*<\\s*" +
        "([a-zA-Z_0-9:]+)[, a-zA-Z_0-9:]*" +
        "\\s*>.+ApiCommand\\s*::\\s*(\\w+).*");

    private static final Pattern firstLineRegexForFunctor = Pattern.compile(
        "\\s*reg\\w*Functor\\w*\\s*<.*");

    private static final Pattern groupRegexForFunctor = Pattern.compile(
        "\\s*reg\\w*Functor\\w*\\s*<\\s*" +
            "([a-zA-Z_0-9:]+)" +
            "\\s*,\\s*" +
            "(\\w+)" +
            "\\s*>.+ApiCommand\\s*::\\s*(\\w+).*");
}
