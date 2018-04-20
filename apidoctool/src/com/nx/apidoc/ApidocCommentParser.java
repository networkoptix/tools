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
    private int indentLevel = 0;

    public static class FunctionDescription 
    {
        public String urlPrefix;
        public Apidoc.Function function;
    }

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
     * @return Empty list if the comment should not convert to an XML function.
     */
    public List<FunctionDescription> createFunctionsFromCommentLines(ApidocTagParser parser)
        throws Error
    {
        parser.parseNextItem();

        final List<FunctionDescription> functions = new ArrayList<FunctionDescription>();
        if (parser.getItem() == null || !TAG_APIDOC.equals(parser.getItem().getTag()))
            throw new Error("Comment should start with " + TAG_APIDOC + " tag.");

        while (parser.getItem() != null)
            functions.add(createFunctionFromCommentLines(parser));

        return functions;
    }
    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private FunctionDescription createFunctionFromCommentLines(ApidocTagParser parser) throws Error
    {
        FunctionDescription description = createFunctionFromApidocItem(parser);

        boolean captionParsed = false;
        boolean permissionsParsed = false;
        boolean returnParsed = false;
        description.function.caption = "";
        description.function.result = new Apidoc.Result();
        description.function.result.caption = "";

        parser.parseNextItem();
        while (parser.getItem() != null && !TAG_APIDOC.equals(parser.getItem().getTag()))
        {
            if (TAG_CAPTION.equals(parser.getItem().getTag()))
            {
                captionParsed = checkTagOnce(
                    captionParsed, description.function.name, TAG_CAPTION);
                checkNoAttribute(parser, description.function.name);
                description.function.caption = parser.getItem().getFullText(indentLevel);
                parser.parseNextItem();
            }
            else if (TAG_PERMISSIONS.equals(parser.getItem().getTag()))
            {
                permissionsParsed = checkTagOnce(
                    permissionsParsed, description.function.name, TAG_PERMISSIONS);
                description.function.permissions = parser.getItem().getFullText(indentLevel + 1);
                parser.parseNextItem();
            }
            else if (TAG_PARAM.equals(parser.getItem().getTag()))
            {
                parseFunctionParam(parser, description.function);
            }
            else if (TAG_RETURN.equals(parser.getItem().getTag()))
            {
                returnParsed = checkTagOnce(returnParsed, description.function.name, TAG_RETURN);
                parseFunctionResult(parser, description.function);
            }
            else if (parser.getItem().getTag().startsWith(TAG_COMMENTED_OUT))
            {
                // Ignore: this comment part is not intended for XML.
                parser.parseNextItem();
            }
            else
            {
                throwUnknownTag(parser, description.function.name);
            }
        }

        return description;
    }

    //---------------------------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private FunctionDescription createFunctionFromApidocItem(ApidocTagParser parser) throws Error
    {
        String[] values = Utils.matchRegex(
            functionHeaderRegex, parser.getItem().getFullText(indentLevel));
        if (values == null)
            throw new Error("Wrong " + TAG_APIDOC + " function header.");

        FunctionDescription result = new FunctionDescription();
        result.urlPrefix = values[1];
        result.function = new Apidoc.Function();

        result.function.name = values[2];
        result.function.method = values[0].trim();
        result.function.description = values[3].trim();

        if ("".equals(parser.getItem().getAttribute()))
            result.function.proprietary = false;
        else if (ATTR_PROPRIETARY.equals(parser.getItem().getAttribute()))
            result.function.proprietary = true;
        else
            throwInvalidAttribute(parser, result.function.name);

        return result;
    }

    private void parseFunctionParam(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert TAG_PARAM.equals(parser.getItem().getTag());

        String paramName = parser.getItem().getInitialToken();
        int paramIndentLevel = paramName.length() - paramName.replace(".", "").length() + 1;

        indentLevel += paramIndentLevel;
        Apidoc.Param param = new Apidoc.Param();
        param.description = parser.getItem().getTextAfterInitialToken(indentLevel);

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
        indentLevel -= paramIndentLevel;
    }

    private void parseParamValues(
        ApidocTagParser parser, Apidoc.Function function, Apidoc.Param param)
        throws Error
    {
        indentLevel++;
        while (parser.getItem() != null && !TAG_APIDOC.equals(parser.getItem().getTag()))
        {
            if (TAG_VALUE.equals(parser.getItem().getTag()))
            {
                // ATTENTION: Currently, [proprietary] params are ignored, until supported in XML.
                if (ATTR_PROPRIETARY.equals(parser.getItem().getAttribute()))
                {
                    parser.parseNextItem();
                    continue;
                }
                checkNoAttribute(parser, function.name);
                Apidoc.Value value = new Apidoc.Value();
                value.name = getInitialToken(parser, function.name);
                value.description = parser.getItem().getTextAfterInitialToken(indentLevel);
                param.values.add(value);
                parser.parseNextItem();
            }
            else if (parser.getItem().getTag().startsWith(TAG_COMMENTED_OUT))
            {
                // Ignore: this comment part is not intended for XML.
                parser.parseNextItem();
            }
            else
            {
                break;
            }
        }
        indentLevel--;
    }

    private void fillDefaultFormatParam(
        Apidoc.Param param, String functionName)
        throws Error
    {
        if (!param.name.equals(PARAM_FORMAT))
        {
            throw new Error(ATTR_DEFAULT + " found for param \"" + param.name +
                "\", but supported only for param \"format\"," +
                " in function " + functionName + ".");
        }

        // TODO: Consider defining default "format" in the C++ source code.
        param.optional = true;
        param.description = DEFAULT_FORMAT_DESCRIPTION;
        param.values.add(createValue("ubjson",
            "Universal Binary JSON data format."));
        param.values.add(createValue("json",
            "JSON data format."));
        param.values.add(createValue("xml",
            "XML data format."));
        param.values.add(createValue("csv",
            "CSV data format. In case of a hierarchical structure,\n" +
            "only the top level data is provided."));
    }

    private static Apidoc.Value createValue(String name, String description)
    {
        Apidoc.Value value = new Apidoc.Value();
        value.name = name;
        value.description = description;
        return value;
    }

    private void parseFunctionResult(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert TAG_RETURN.equals(parser.getItem().getTag());
        indentLevel++;
        checkNoAttribute(parser, function.name);
        function.result.caption = parser.getItem().getFullText(indentLevel);

        boolean deprecatedAttributeTagFound = false;
        parser.parseNextItem();
        while (parser.getItem() != null && !TAG_APIDOC.equals(parser.getItem().getTag()))
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
            else if (parser.getItem().getTag().startsWith(TAG_COMMENTED_OUT))
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
                "    WARNING: Deprecated Apidoc tag \"%attribute\" found" +
                    " instead of \"" + TAG_PARAM + "\"" +
                    " in function " + function.name + ".");
        }
        indentLevel--;
    }

    private void parseFunctionResultAttributeDeprecated(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert "%attribute".equals(parser.getItem().getTag());

        Apidoc.Param param = new Apidoc.Param();
        param.description = parser.getItem().getTextAfterInitialToken(indentLevel);

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

    private void parseFunctionResultParam(
        ApidocTagParser parser, Apidoc.Function function)
        throws Error
    {
        assert TAG_PARAM.equals(parser.getItem().getTag());

        String paramName = parser.getItem().getInitialToken();
        int paramIndentLevel = paramName.length() - paramName.replace(".", "").length() + 1;

        indentLevel += paramIndentLevel;

        Apidoc.Param param = new Apidoc.Param();
        param.description = parser.getItem().getTextAfterInitialToken(indentLevel);

        param.name = getInitialToken(parser, function.name);
        for (Apidoc.Param existingParam: function.result.params)
        {
            if (existingParam.name.equals(param.name))
            {
                throw new Error("Duplicate result param \"" + param.name + "\" found" +
                    " in function " + function.name + ".");
            }
        }

        param.optional = false;
        if ("".equals(parser.getItem().getAttribute()))
            param.proprietary = false;
        else if (ATTR_PROPRIETARY.equals(parser.getItem().getAttribute()))
            param.proprietary = true;
        else
            throwInvalidAttribute(parser, function.name);

        parser.parseNextItem();

        parseParamValues(parser, function, param);

        function.result.params.add(param);
        indentLevel -= paramIndentLevel;
    }

    /**
     * @return New value for the tagParsed flag.
     */
    private static boolean checkTagOnce(
        boolean tagParsed, String functionName, String tag)
        throws Error
    {
        if (tagParsed)
        {
            throw new Error("More than one " + tag + " found" +
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
        throw new Error("The attribute " + parser.getItem().getAttribute() +
            " is not allowed after the tag " + parser.getItem().getTag() +
            " in function " + functionName + ".");
    }

    private static void checkNoAttribute(
        ApidocTagParser parser, String functionName)
        throws Error
    {
        if (!parser.getItem().getAttribute().isEmpty())
            throwInvalidAttribute(parser, functionName);
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

    //---------------------------------------------------------------------------------------------

    private static final Pattern functionHeaderRegex = Pattern.compile(
        "\\s*([A-Z]+ )?\\s*(?:(/\\w+)/)?([\\w\\/]+)(.*)", Pattern.DOTALL);
      //     0HttpMthd        1UrlPre   2FnNm      3Txt
      //       GET             /ec2     getRe      \nRe
}
