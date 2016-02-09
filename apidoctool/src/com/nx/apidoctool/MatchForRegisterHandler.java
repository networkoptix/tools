package com.nx.apidoctool;

import com.nx.apidoc.ApidocCommentParser;
import com.nx.util.SourceCode;

import java.util.regex.Pattern;

/**
 * Parses SourceCode for registration line "register...Handler" of an API
 * function, and then represents the match.
 */
public final class MatchForRegisterHandler
{
    public final int indent;

    public final String functionName;

    /**
     * Null if no input data structure is defined for this API function.
     */
    public final String inputDataType;

    /**
     * Null if no output data structure is defined for this API function.
     */
    public final String outputDataType;

    public final String method;

    //--------------------------------------------------------------------------

    /**
     * @return Null if the line is not a registration line.
     */
    public static MatchForRegisterHandler create(
        SourceCode sourceCode, int line)
        throws SourceCode.Error, ApidocCommentParser.Error
    {
        String[] params;

        params = sourceCode.matchMultiline(line,
            firstLineRegexForGetFunc, groupRegexForGetFunc, lastLineRegex);
        if (params != null)
        {
            return new MatchForRegisterHandler(sourceCode.getLineIndent(line),
                params[2], params[0], params[1], "GET");
        }

        params = sourceCode.matchMultiline(line,
            firstLineRegexForUpdateFunc, groupRegexForUpdateFunc, lastLineRegex);
        if (params != null)
        {
            return new MatchForRegisterHandler(sourceCode.getLineIndent(line),
                params[1], params[0], null, "POST");
        }

        params = sourceCode.matchMultiline(line,
            firstLineRegexForFunctor, groupRegexForFunctor, lastLineRegex);
        if (params != null)
        {
            return new MatchForRegisterHandler(sourceCode.getLineIndent(line),
                params[2], params[0], params[1], "GET");
        }

        return null;
    }

    //--------------------------------------------------------------------------

    private MatchForRegisterHandler(
        int indent,
        String functionName,
        String inputDataType,
        String outputDataType,
        String method)
    {
        assert functionName != null;
        assert !functionName.isEmpty();
        assert inputDataType == null || !inputDataType.isEmpty();
        assert outputDataType == null || !outputDataType.isEmpty();
        assert method != null;
        assert !method.isEmpty();

        if ("std::nullptr_t".equals(inputDataType))
            inputDataType = null;

        this.indent = indent;
        this.functionName = functionName;
        this.inputDataType = inputDataType;
        this.outputDataType = outputDataType;
        this.method = method;
    }

    //--------------------------------------------------------------------------

    private static final Pattern lastLineRegex = Pattern.compile(
        ".*[;\\[].*");

    private static final Pattern firstLineRegexForGetFunc = Pattern.compile(
        "\\s*registerGetFuncHandler\\s*<.*");

    private static final Pattern groupRegexForGetFunc = Pattern.compile(
        "\\s*registerGetFuncHandler\\s*<\\s*" +
        "([a-zA-Z_0-9:]+)" +
        "\\s*,\\s*" +
        "(\\w+)" +
        "\\s*>.+ApiCommand\\s*::\\s*(\\w+).*");

    private static final Pattern firstLineRegexForUpdateFunc = Pattern.compile(
        "\\s*registerUpdateFuncHandler\\s*<.*");

    private static final Pattern groupRegexForUpdateFunc = Pattern.compile(
        "\\s*registerUpdateFuncHandler\\s*<\\s*" +
        "([a-zA-Z_0-9:]+)" +
        "\\s*>.+ApiCommand\\s*::\\s*(\\w+).*");

    private static final Pattern firstLineRegexForFunctor = Pattern.compile(
        "\\s*registerFunctorHandler\\s*<.*");

    private static final Pattern groupRegexForFunctor = Pattern.compile(
        "\\s*registerFunctorHandler\\s*<\\s*" +
            "([a-zA-Z_0-9:]+)" +
            "\\s*,\\s*" +
            "(\\w+)" +
            "\\s*>.+ApiCommand\\s*::\\s*(\\w+).*");
}
