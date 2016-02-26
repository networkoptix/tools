package com.nx.apidoc;

import com.nx.util.Utils;

import java.util.*;
import java.util.regex.Pattern;

/**
 * Parser for Apidoc Comments to Apidoc structure elements for XML.
 */
public final class ApidocCommentParser
    extends ApidocComment
{
    private ApidocCommentParser() {}

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

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    public static Apidoc.Function createFunctionFromCommentLines(
        List<String> lines,
        String expectedUrlPrefix,
        String expectedFunctionName)
        throws Error
    {
        ApidocTagParser parser = new ApidocTagParser(lines);
        parser.parseNextItem();

        Apidoc.Function function = createFunctionFromApidocItem(
            parser, expectedUrlPrefix, expectedFunctionName);
        if (function == null)
            return null;

        boolean captionParsed = false;
        boolean returnParsed = false;
        function.caption = "";
        function.result = new Apidoc.Result();
        function.result.caption = "";

        parser.parseNextItem();
        while (parser.getItem() != null)
        {
            if (TAG_CAPTION.equals(parser.getItem().getTag()))
            {
                captionParsed = checkTagOnce(captionParsed, function.name);
                checkNoAttribute(parser, function.name);
                function.caption = parser.getItem().getFullText();
                parser.parseNextItem();
            }
            else if (TAG_PARAM.equals(parser.getItem().getTag()))
            {
                parseFunctionParam(parser, function);
            }
            else if (TAG_RETURN.equals(parser.getItem().getTag()))
            {
                returnParsed = checkTagOnce(returnParsed, function.name);
                parseFunctionResult(parser, function);
            }
            else if (TAG_PRIVATE.equals(parser.getItem().getTag()))
            {
                // Ignore: this comment part is not intended for XML.
                parser.parseNextItem();
            }
            else
            {
                throwUnknownTag(parser, function.name);
            }
        }

        return function;
    }

    //--------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private static Apidoc.Function createFunctionFromApidocItem(
        ApidocTagParser parser,
        String expectedUrlPrefix,
        String expectedFunctionName)
        throws Error
    {
        if (parser.getItem() == null ||
            !TAG_APIDOC.equals(parser.getItem().getTag()))
        {
            throw new Error("Comment should start with " + TAG_APIDOC + " tag" +
                " in function " + expectedFunctionName + ".");
        }

        String[] values = Utils.matchRegex(
            functionHeaderRegex, parser.getItem().getFullText());
        if (values == null)
        {
            throw new Error("Wrong " + TAG_APIDOC + " function header" +
                " in function " + expectedFunctionName + ".");
        }

        final String urlPrefix = values[1] == null ? "" : values[1];
        if (!urlPrefix.equals(expectedUrlPrefix))
            return null; //< The function belongs to a different group.

        Apidoc.Function function = new Apidoc.Function();

        function.name = values[2] == null ? "" : values[2];
        if (!function.name.equals(expectedFunctionName))
        {
            throw new Error(TAG_APIDOC + " function name \"" + function.name +
                "\" does not match C++ code" +
                " in function " + expectedFunctionName + ".");
        }

        function.method = values[0] == null ? "" : values[0].trim();
        function.description = new Apidoc.Description();
        function.description.xml = values[3].trim();

        if ("".equals(parser.getItem().getAttribute()))
        {
            function.proprietary = false;
        }
        else if (ATTR_PROPRIETARY.equals(parser.getItem().getAttribute()))
        {
            function.proprietary = true;
        }
        else
        {
            throwInvalidAttribute(parser, function.name);
        }

        return function;
    }

    private static void parseFunctionParam(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert TAG_PARAM.equals(parser.getItem().getTag());

        Apidoc.Param param = new Apidoc.Param();
        param.description = new Apidoc.Description();
        param.description.xml = parser.getItem().getTextAfterInitialToken();

        param.name = getInitialToken(parser, function.name);
        for (Apidoc.Param existingParam: function.params)
        {
            if (existingParam.name.equals(param.name))
            {
                throw new Error("Duplicate param \"" + param.name + "\" found" +
                    " in function " + function.name + ".");
            }
        }

        if ("".equals(parser.getItem().getAttribute()))
        {
            param.proprietary = false;
            param.optional = false;
        }
        else if (ATTR_PROPRIETARY.equals(parser.getItem().getAttribute()))
        {
            param.proprietary = true;
            param.optional = true;
        }
        else if (ATTR_OPT.equals(parser.getItem().getAttribute()))
        {
            param.proprietary = false;
            param.optional = true;
        }
        else if (ATTR_DEFAULT.equals(parser.getItem().getAttribute()))
        {
            fillDefaultFormatParam(param, function.name);
        }
        else
        {
            throwInvalidAttribute(parser, function.name);
        }

        parser.parseNextItem();

        parseParamValues(parser, function, param);

        function.params.add(param);
    }

    private static void parseParamValues(
        ApidocTagParser parser, Apidoc.Function function, Apidoc.Param param)
        throws Error
    {
        while (parser.getItem() != null)
        {
            if (TAG_VALUE.equals(parser.getItem().getTag()))
            {
                checkNoAttribute(parser, function.name);
                Apidoc.Value value = new Apidoc.Value();
                value.name = getInitialToken(parser, function.name);
                value.description = new Apidoc.Description();
                value.description.xml = parser.getItem().getTextAfterInitialToken();
                param.values.add(value);
                parser.parseNextItem();
            }
            else if (TAG_PRIVATE.equals(parser.getItem().getTag()))
            {
                // Ignore: this comment part is not intended for XML.
                parser.parseNextItem();
            }
            else
            {
                break;
            }
        }
    }

    private static void fillDefaultFormatParam(
        Apidoc.Param param, String functionName)
        throws Error
    {
        if (!param.name.equals(PARAM_FORMAT))
        {
            throw new Error(ATTR_DEFAULT + " found for param \"" + param.name +
                "\", but supported only for param \"format\"," +
                " in function " + functionName + ".");
        }

        // TODO: Consider defining default "format" in the Source Code.
        param.optional = true;
        param.description.xml = DEFAULT_FORMAT_DESCRIPTION;
        param.values.add(createValue("ubjson",
            "universal binary json data format"));
        param.values.add(createValue("json",
            "json data format"));
        param.values.add(createValue("xml",
            "xml data format"));
        param.values.add(createValue("csv",
            "CSV data format. In case of hierarchical structure only\n" +
            "top level data will be provided"));
    }

    private static Apidoc.Value createValue(String name, String description)
    {
        Apidoc.Value value = new Apidoc.Value();
        value.name = name;
        value.description = new Apidoc.Description();
        value.description.xml = description;
        return value;
    }

    private static void parseFunctionResult(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert TAG_RETURN.equals(parser.getItem().getTag());
        checkNoAttribute(parser, function.name);
        function.result.caption = parser.getItem().getFullText();

        boolean deprecatedAttributeTagFound = false;
        parser.parseNextItem();
        while (parser.getItem() != null)
        {
            if (TAG_PARAM.equals(parser.getItem().getTag()))
            {
                parseFunctionResultParam(parser, function);
            }
            else if ("%attribute".equals(parser.getItem().getTag()))
            {
                // Support for old deprecated Apidoc Comment format which has
                // "%attribute" tags following "%result" instead of "%param".
                deprecatedAttributeTagFound = true;
                parseFunctionResultAttributeDeprecated(parser, function);
            }
            else if (TAG_PRIVATE.equals(parser.getItem().getTag()))
            {
                // Ignore: this comment part is not intended for XML.
                parser.parseNextItem();
            }
            else
            {
                break;
            }
        }

        if (deprecatedAttributeTagFound)
        {
            System.out.println(
                "WARNING: Deprecated Apidoc tag \"%attribute\" found" +
                    " instead of \"" + TAG_PARAM + "\"" +
                    " in function " + function.name + ".");
        }
    }

    private static void parseFunctionResultAttributeDeprecated(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert "%attribute".equals(parser.getItem().getTag());

        Apidoc.Param param = new Apidoc.Param();
        param.description = new Apidoc.Description();
        param.description.xml = parser.getItem().getTextAfterInitialToken();

        param.name = getInitialToken(parser, function.name);
        for (Apidoc.Param existingParam: function.result.params)
        {
            if (existingParam.name.equals(param.name))
            {
                throw new Error("Duplicate result attribute \"" + param.name + "\" found" +
                    " in function " + function.name + ".");
            }
        }

        checkNoAttribute(parser, function.name);
        param.proprietary = false;
        param.optional = false;

        parser.parseNextItem();

        function.result.params.add(param);
    }

    private static void parseFunctionResultParam(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert TAG_PARAM.equals(parser.getItem().getTag());

        Apidoc.Param param = new Apidoc.Param();
        param.description = new Apidoc.Description();
        param.description.xml = parser.getItem().getTextAfterInitialToken();

        param.name = getInitialToken(parser, function.name);
        for (Apidoc.Param existingParam: function.result.params)
        {
            if (existingParam.name.equals(param.name))
            {
                throw new Error("Duplicate result param \"" + param.name + "\" found" +
                    " in function " + function.name + ".");
            }
        }

        checkNoAttribute(parser, function.name);
        param.proprietary = false;
        param.optional = false;

        parser.parseNextItem();

        parseParamValues(parser, function, param);

        function.result.params.add(param);
    }

    /**
     * @return New value for the tagParsed flag.
     */
    private static boolean checkTagOnce(boolean tagParsed, String functionName)
        throws Error
    {
        if (tagParsed)
        {
            throw new Error("More than one " + TAG_CAPTION + " found" +
                " in function " + functionName + ".");
        }
        return true;
    }

    private static void throwUnknownTag(
        ApidocTagParser parser, String functionName)
        throws Error
    {
        throw new Error("Unknown tag " + parser.getItem().getTag() + " found" +
            " in function " + functionName + ".");
    }

    private static void throwInvalidAttribute(
        ApidocTagParser parser, String functionName)
        throws Error
    {
        final String attribute = parser.getItem().getAttribute();
        throw new Error("An attribute [" + attribute + "]" +
            " is not allowed after the tag " + parser.getItem().getTag() +
            " in function " + functionName + ".");
    }

    private static void checkNoAttribute(
        ApidocTagParser parser, String functionName)
        throws Error
    {
        final String attribute = parser.getItem().getAttribute();
        if (!attribute.isEmpty())
        {
            throw new Error("The [" + attribute + "]" +
                " is not allowed after the tag " + parser.getItem().getTag() +
                " in function " + functionName + ".");
        }
    }

    private static String getInitialToken(
        ApidocTagParser parser, String functionName)
        throws Error
    {
        final String initialToken = parser.getItem().getInitialToken();

        if (initialToken.isEmpty())
        {
            throw new Error(
                "A token should follow the tag " + parser.getItem().getTag() +
                " in function " + functionName + ".");
        }

        return initialToken;
    }

    //--------------------------------------------------------------------------

    private static final Pattern functionHeaderRegex = Pattern.compile(
        "\\s*([A-Z]+ )?\\s*(?:(/\\w+)/)?(\\w+)(.*)", Pattern.DOTALL);
}
