package com.nx.apidoc;

import com.nx.util.Utils;

import java.io.UnsupportedEncodingException;
import java.net.URLDecoder;
import java.util.*;
import java.util.regex.Pattern;

/**
 * Parser for Apidoc Comments to Apidoc structure elements for XML.
 */
public final class ApidocCommentParser
    extends ApidocComment
{
    private int indentLevel = 0;

    public enum ParamDirection
    {
        Input,
        Output
    }

    public enum ParamMode
    {
        WithToken,
        WithoutToken
    }

    public static class FunctionDescription 
    {
        public String urlPrefix;
        public String inputStructName;
        public boolean inputIsOptional = false;
        public Apidoc.Function function;
    }

    public static final class Error
        extends Exception
    {
        public Error(String message) { super(message); }
    }

    public static Apidoc.Param parseParam(
        List<ApidocTagParser.Item> tags, ParamDirection paramDirection, ParamMode paramMode)
        throws Error
    {
        if (tags == null)
            return null;

        final ApidocCommentParser parser = new ApidocCommentParser();
        final ListIterator<ApidocTagParser.Item> tagIterator = tags.listIterator();
        if (tagIterator.hasNext())
        {
            final ApidocTagParser.Item item = tagIterator.next();

            final Apidoc.Param result =
                parser.parseParam(item, tagIterator, paramDirection, paramMode);

            if (tagIterator.hasNext())
            {
                final ApidocTagParser.Item unexpectedItem = tagIterator.next();
                throw new Error(unexpectedItem.getErrorPrefix() +
                    "Unexpected tag " + unexpectedItem.getTag() + " found.");
            }
            return result;
        }
        return null; //< No tags found.
    }

    public static List<Apidoc.Param> parseParams(
        List<ApidocTagParser.Item> tags, String namePrefix, ParamDirection paramDirection, ParamMode paramMode)
        throws Error
    {
        List<Apidoc.Param> result = new ArrayList<Apidoc.Param>();
        if (tags == null)
            return result;
        final ApidocCommentParser parser = new ApidocCommentParser();
        final ListIterator<ApidocTagParser.Item> tagIterator = tags.listIterator();
        while (tagIterator.hasNext())
        {
            final ApidocTagParser.Item item = tagIterator.next();
            if (TAG_PARAM.equals(item.getTag()))
            {
                final Apidoc.Param param =
                        parser.parseParam(item, tagIterator, paramDirection, paramMode);
                checkDuplicateParam(item, result, param.name);
                param.name = namePrefix + param.name;
                result.add(param);
            }
        }
        return result;
    }

    /**
     * @return Empty list if the comment should not convert to an XML function.
     */
    public List<FunctionDescription> createFunctionsFromTags(
        List<ApidocTagParser.Item> tags,
        TypeManager typeManager,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit)
        throws
            Error,
            TypeManager.Error

    {
        final List<FunctionDescription> functions = new ArrayList<FunctionDescription>();

        ListIterator<ApidocTagParser.Item> tagIterator = tags.listIterator();
        while (tagIterator.hasNext())
        {
            functions.add(createFunctionFromTags(
                tagIterator, typeManager, requiredFunctionCaptionLenLimit, requiredGroupNameLenLimit));
        }

        return functions;
    }

    private static final class Param
    {
        List<Apidoc.Value> values;
        String structName;
        String deprecatedDescription = "";
    }

    //---------------------------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private FunctionDescription createFunctionFromTags(
        ListIterator<ApidocTagParser.Item> tagIterator,
        TypeManager typeManager,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit)
        throws
            Error,
            TypeManager.Error
    {
        ApidocTagParser.Item item = tagIterator.next();

        if (!TAG_APIDOC.equals(item.getTag()))
        {
            throw new Error(item.getErrorPrefix() +
                "Comment should start with " + TAG_APIDOC + " tag.");
        }

        final String firstItemErrorPrefix = item.getErrorPrefix();
        boolean captionParsed = false;
        boolean permissionsParsed = false;
        boolean returnParsed = false;

        FunctionDescription description = createFunctionFromApidocItem(item);
        description.function.caption = "";
        description.function.result = new Apidoc.Result();
        description.function.result.caption = "";
        description.function.result.type = Apidoc.Type.values()[0];

        while (tagIterator.hasNext())
        {
            item = tagIterator.next();
            if (TAG_APIDOC.equals(item.getTag()))
            {
                tagIterator.previous(); //< Return previous tag for future parsing.
                break;
            }
            else if (TAG_STRUCT.equals(item.getTag()))
            {
                description.inputStructName = item.getFullText(indentLevel);
                if (ATTR_OPT.equals(item.getAttribute()))
                    description.inputIsOptional = true;
            }
            else if (TAG_CAPTION.equals(item.getTag()))
            {
                captionParsed = checkTagOnce(item, captionParsed, TAG_CAPTION);
                checkNoAttribute(item);
                final String value = item.getFullText(indentLevel).trim();
                if (value.isEmpty())
                    throw new Error(item.getErrorPrefix() + "Empty " + TAG_CAPTION);
                if (requiredFunctionCaptionLenLimit > 0 && value.length() > requiredFunctionCaptionLenLimit)
                    throw new Error(item.getErrorPrefix() + TAG_CAPTION + " is too long.");
                description.function.caption = value;
            }
            else if (TAG_INGROUP.equals(item.getTag()))
            {
                checkNoAttribute(item);
                final String value = item.getFullText(indentLevel).trim();
                if (value.isEmpty())
                    throw new Error(item.getErrorPrefix() + "Empty " + TAG_INGROUP);
                if (requiredGroupNameLenLimit > 0 && value.length() > requiredFunctionCaptionLenLimit)
                    throw new Error(item.getErrorPrefix() + TAG_INGROUP + " is too long.");
                if (description.function.groups.contains(value))
                {
                    throw new Error(item.getErrorPrefix() + "The " + TAG_INGROUP + " " + value +
                        " is specified more than once.");
                }
                description.function.groups.add(value);
            }
            else if (TAG_PERMISSIONS.equals(item.getTag()))
            {
                permissionsParsed = checkTagOnce(item, permissionsParsed, TAG_PERMISSIONS);
                description.function.permissions = item.getFullText(indentLevel + 1);
            }
            else if (TAG_PARAM.equals(item.getTag()))
            {
                final Apidoc.Param param = parseParam(
                    item, tagIterator, ParamDirection.Input, ParamMode.WithToken);

                checkDuplicateParam(item, description.function.params, param.name);
                if (param.unused)
                    description.function.unusedParams.add(param);
                else
                    description.function.params.add(param);

                addStructParams(
                    description.function.params,
                    description.function.unusedParams,
                    param,
                    typeManager,
                    ParamDirection.Input);
            }
            else if (TAG_RETURN.equals(item.getTag()))
            {
                returnParsed = checkTagOnce(item, returnParsed, TAG_RETURN);
                final Apidoc.Result result = parseFunctionResult(
                    item, tagIterator, typeManager);
                description.function.result = result;
            }
            else if (!item.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                throwUnknownTag(item);
            }
        }

        if (requiredFunctionCaptionLenLimit >= 0 && description.function.caption.isEmpty())
            throw new Error(firstItemErrorPrefix + TAG_CAPTION + " unspecified.");
        if (requiredGroupNameLenLimit >= 0 && description.function.groups.isEmpty())
            throw new Error(firstItemErrorPrefix + TAG_INGROUP + " unspecified.");

        return description;
    }

    private void addStructParams(
        List<Apidoc.Param> params,
        List<Apidoc.Param> unusedParams,
        Apidoc.Param param,
        TypeManager typeManager,
        ParamDirection direction)
        throws TypeManager.Error,
        Error
    {
        if (typeManager != null && param.structName != null)
        {
            if (param.type != Apidoc.Type.ARRAY && param.type != Apidoc.Type.OBJECT &&
                param.type != Apidoc.Type.UNKNOWN)
            {
                throw new Error("Param '" + param.name + "' has '%struct' tag, but param type is '" +
                    param.type + "'" + ". To use '%struct' tag type should be 'object' or 'array'");
            }
            String prefix = param.name;
            if (param.type == Apidoc.Type.ARRAY)
                prefix += "[].";
            else
                prefix += ".";
            List<Apidoc.Param> structParams = typeManager.getStructParams(
                param.structName, prefix, direction);
            if (structParams != null)
            {
                for (Apidoc.Param structParam: structParams)
                {
                    structParam.isGeneratedFromStruct = true;
                    if (structParam.unused)
                        unusedParams.add(structParam);
                    else
                        params.add(structParam);
                }
            }
        }
    }

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private FunctionDescription createFunctionFromApidocItem(ApidocTagParser.Item item)
        throws Error
    {
        String[] values = Utils.matchRegex(
            functionHeaderRegex, item.getFullText(indentLevel));
        if (values == null)
            throw new Error(item.getErrorPrefix() + "Wrong " + TAG_APIDOC + " function header.");

        FunctionDescription result = new FunctionDescription();
        result.urlPrefix = values[1];
        result.function = new Apidoc.Function();

        result.function.method = values[0].trim();
        try
        {
            result.function.name = URLDecoder.decode(values[2], "UTF-8");
        }
        catch (UnsupportedEncodingException e)
        {
            result.function.name = values[2];
        }
        result.function.description = values[3].trim();
        if (LABEL_ARRAY_PARAMS.equals(item.getLabel()))
            result.function.arrayParams = true;
        else if (!"".equals(item.getLabel()))
            throw new Error(item.getErrorPrefix() + "Invalid label: \"" + item.getLabel() + "\"");

        if ("".equals(item.getAttribute()))
            result.function.proprietary = false;
        else if (ATTR_PROPRIETARY.equals(item.getAttribute()))
            result.function.proprietary = true;
        else
            throwInvalidAttribute(item);

        return result;
    }

    private Apidoc.Param parseParam(
        ApidocTagParser.Item item,
        ListIterator<ApidocTagParser.Item> tagIterator,
        ParamDirection paramDirection,
        ParamMode paramMode)
        throws Error
    {
        int paramIndentLevel = 0;
        if (paramMode == ParamMode.WithToken)
        {
            final String paramName = item.getInitialToken();
            paramIndentLevel = Utils.substringCount(paramName, ".") + 1;
        }
        indentLevel += paramIndentLevel;

        Apidoc.Param param = new Apidoc.Param();
        if (paramMode == ParamMode.WithToken)
            param.description = item.getTextAfterInitialToken(indentLevel);
        else
            param.description = item.getFullText(indentLevel);
        param.name = getInitialToken(item, paramMode);
        try
        {
            param.type = Apidoc.Type.fromString(item.getLabel());
        }
        catch (Exception e)
        {
            throw new Error(item.getErrorPrefix() + "Invalid param type \"" + item.getLabel()
                + "\" found.");
        }
        Param paramDescription = parseParamItems(tagIterator);
        param.values.addAll(paramDescription.values);
        param.structName = paramDescription.structName;
        if (!paramDescription.deprecatedDescription.isEmpty())
            param.description = paramDescription.deprecatedDescription + "\n" + param.description;

        if (paramDirection == ParamDirection.Output)
            parseFunctionResultParamAttr(item, param);
        else
            parseFunctionParamAttr(item, param);

        indentLevel -= paramIndentLevel;
        return param;
    }

    private static void parseFunctionParamAttr(ApidocTagParser.Item item, Apidoc.Param param)
        throws Error
    {
        if ("".equals(item.getAttribute()))
        {
            param.proprietary = false;
            param.optional = false;
        }
        else if (ATTR_PROPRIETARY.equals(item.getAttribute()))
        {
            param.proprietary = true;
            param.optional = true;
        }
        else if (ATTR_READONLY.equals(item.getAttribute()))
        {
            param.readonly = true;
            param.optional = true;
        }
        else if (ATTR_OPT.equals(item.getAttribute()))
        {
            param.proprietary = false;
            param.optional = true;
        }
        else if (ATTR_DEFAULT.equals(item.getAttribute()))
        {
            fillDefaultFormatParam(item, param);
            param.hasDefaultDescription = true;
        }
        else if (ATTR_REF.equals(item.getAttribute()))
        {
            param.isRef = true;
        }
        else if (ATTR_UNUSED.equals(item.getAttribute()))
        {
            param.unused = true;
        }
        else
        {
            throwInvalidAttribute(item);
        }
    }

    private Param parseParamItems(
        ListIterator<ApidocTagParser.Item> itemIterator)
        throws Error
    {
        indentLevel++;
        final Param paramDescription = new Param();
        paramDescription.values = new ArrayList<Apidoc.Value>();
        while (itemIterator.hasNext())
        {
            final ApidocTagParser.Item item = itemIterator.next();
            if (TAG_VALUE.equals(item.getTag()))
            {
                // ATTENTION: Currently, [proprietary] values are ignored, until supported in XML.
                if (ATTR_PROPRIETARY.equals(item.getAttribute()))
                    continue;

                checkNoAttribute(item);
                Apidoc.Value value = new Apidoc.Value();
                value.name = getInitialToken(item, ParamMode.WithToken);
                value.description = item.getTextAfterInitialToken(indentLevel);
                paramDescription.values.add(value);
            }
            else if (TAG_STRUCT.equals(item.getTag()))
            {
                paramDescription.structName = item.getFullText(indentLevel);
            }
            else if (TAG_DEPRECATED.equals(item.getTag()))
            {
                paramDescription.deprecatedDescription = item.getFullText(indentLevel);
            }
            else if (!item.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                itemIterator.previous(); //< Return previous item for future parsing.
                break;
            }
        }
        indentLevel--;
        return paramDescription;
    }

    private static void fillDefaultFormatParam(ApidocTagParser.Item item, Apidoc.Param param)
        throws Error
    {
        if (!param.name.equals(PARAM_FORMAT))
        {
            throw new Error(item.getErrorPrefix() + ATTR_DEFAULT + " found for param \""
                + param.name + "\", but supported only for param \"format\".");
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

    private Apidoc.Result parseFunctionResult(
        ApidocTagParser.Item item,
        ListIterator<ApidocTagParser.Item> tagIterator,
        TypeManager typeManager)
        throws Error,
        TypeManager.Error
    {
        assert TAG_RETURN.equals(item.getTag());
        indentLevel++;
        checkNoAttribute(item);
        Apidoc.Result result = new Apidoc.Result();
        result.caption = item.getFullText(indentLevel);
        try
        {
            result.type = Apidoc.Type.fromString(item.getLabel());
        }
        catch (Exception e)
        {
            throw new Error(item.getErrorPrefix() + "Invalid result type \"" + item.getLabel()
                + "\" found.");
        }

        boolean deprecatedAttributeTagFound = false;
        while (tagIterator.hasNext())
        {
            item = tagIterator.next();
            if (TAG_STRUCT.equals(item.getTag()))
            {
                result.outputStructName = item.getFullText(indentLevel);
            }
            else if (TAG_PARAM.equals(item.getTag()))
            {
                Apidoc.Param param = parseParam(
                    item, tagIterator, ParamDirection.Output, ParamMode.WithToken);

                checkDuplicateParam(item, result.params, param.name);
                if (param.unused)
                    result.unusedParams.add(param);
                else
                    result.params.add(param);

                addStructParams(
                    result.params,
                    result.unusedParams,
                    param,
                    typeManager,
                    ParamDirection.Output);
            }
            else if ("%attribute".equals(item.getTag()))
            {
                // Support for old deprecated Apidoc Comment format which has
                // "%attribute" tags following "%result" instead of "%param".
                deprecatedAttributeTagFound = true;
                parseFunctionResultAttributeDeprecated(item, result);
            }
            else if (!item.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                tagIterator.previous(); //< Return previous tag for future parsing.
                break;
            }
        }

        if (deprecatedAttributeTagFound)
        {
            System.out.println(
                "    WARNING: Deprecated Apidoc tag \"%attribute\" found" +
                    " instead of \"" + TAG_PARAM + "\".");
        }
        indentLevel--;
        return result;
    }

    private void parseFunctionResultAttributeDeprecated(
        ApidocTagParser.Item item, Apidoc.Result result)
        throws Error
    {
        assert "%attribute".equals(item.getTag());

        Apidoc.Param param = new Apidoc.Param();
        param.description = item.getTextAfterInitialToken(indentLevel);

        param.name = getInitialToken(item, ParamMode.WithToken);
        for (Apidoc.Param existingParam: result.params)
        {
            if (existingParam.name.equals(param.name))
            {
                throw new Error(item.getErrorPrefix() + "Duplicate result attribute \"" + param.name
                    + "\" found.");
            }
        }

        checkNoAttribute(item);
        param.proprietary = false;
        param.optional = false;
        result.params.add(param);
    }

    private void parseFunctionResultParamAttr(ApidocTagParser.Item tag, Apidoc.Param param)
        throws Error
    {
        if (ATTR_PROPRIETARY.equals(tag.getAttribute()))
            param.proprietary = true;
        else if (ATTR_UNUSED.equals(tag.getAttribute()))
            param.unused = true;
        else if (ATTR_READONLY.equals(tag.getAttribute()))
            param.readonly = true;
        else if (ATTR_OPT.equals(tag.getAttribute()))
            param.optional = true;
        else if (!"".equals(tag.getAttribute()))
            throwInvalidAttribute(tag);
    }

    /**
     * @return New value for the tagParsed flag.
     */
    private boolean checkTagOnce(ApidocTagParser.Item item, boolean tagParsed, String tag)
        throws Error
    {
        if (tagParsed)
            throw new Error(item.getErrorPrefix() + "More than one " + tag + " found.");

        return true;
    }

    private void throwUnknownTag(ApidocTagParser.Item item)
        throws Error
    {
        throw new Error(item.getErrorPrefix() + "Unknown tag " + item.getTag() + " found.");
    }

    private static void throwInvalidAttribute(ApidocTagParser.Item item)
        throws Error
    {
        throw new Error(item.getErrorPrefix() + "The attribute " + item.getAttribute() +
            " is not allowed after the tag " + item.getTag() + ".");
    }

    private void checkNoAttribute(ApidocTagParser.Item item)
        throws Error
    {
        if (!item.getAttribute().isEmpty())
            throwInvalidAttribute(item);
    }

    private static void checkDuplicateParam(
        ApidocTagParser.Item item, List<Apidoc.Param> params, String paramName)
        throws Error
    {
        // Overwrite param that was generated by %struct tag.
        Iterator<Apidoc.Param> iterator = params.iterator();
        while (iterator.hasNext())
        {
            final Apidoc.Param existingParam = iterator.next();
            if (existingParam.isGeneratedFromStruct && existingParam.name.equals(paramName))
                iterator.remove();
        }
        for (Apidoc.Param existingParam: params)
        {
            if (existingParam.name.equals(paramName))
            {
                throw new Error(item.getErrorPrefix() + "Duplicate param \"" + paramName
                    + "\" found.");
            }
        }
    }

    private String getInitialToken(ApidocTagParser.Item item, ParamMode paramMode)
        throws Error
    {
        if (paramMode == ParamMode.WithoutToken)
            return "";

        final String initialToken = item.getInitialToken();

        if (initialToken.isEmpty())
        {
            throw new Error(item.getErrorPrefix()
                + "A token should follow the tag " + item.getTag() + ".");
        }

        return initialToken;
    }

    //---------------------------------------------------------------------------------------------

    private static final Pattern functionHeaderRegex = Pattern.compile(
        "\\s*([A-Z]+ )?\\s*(?:(/\\w+)/)?(\\w[\\w%\\{\\}/\\?-]*)(.*)", Pattern.DOTALL);
    //       0HttpMthd        1UrlPre   2FnNm                  3Txt
    //       GET              /ec2      getRe                  \nRe
}
