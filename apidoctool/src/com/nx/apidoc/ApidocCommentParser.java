// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.apidoctool.Replacement;
import com.nx.utils.*;

import java.io.UnsupportedEncodingException;
import java.net.URLDecoder;
import java.util.*;
import java.util.regex.Pattern;

/**
 * Parser for Apidoc Comments to Apidoc structure elements.
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
        public String urlPrefix = "";
        public Apidoc.Function function = new Apidoc.Function();
    }

    public static final class Error
        extends Exception
    {
        public Error(String message) { super(message); }
    }

    public static Apidoc.Param parseParam(
        List<ApidocTagParser.Item> tags,
        ParamDirection paramDirection,
        ParamMode paramMode)
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
        List<ApidocTagParser.Item> tags,
        String namePrefix,
        ParamDirection paramDirection,
        ParamMode paramMode)
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

    public enum FunctionType
    {
        API,
        TRANSACTION,
    }

    /**
     * @return Empty list if the comment should not convert to a Function.
     */
    public List<FunctionDescription> createFunctionsFromTags(
        List<ApidocTagParser.Item> tags,
        TypeManager typeManager,
        List<Apidoc.Group> groups,
        List<Replacement> urlPrefixReplacements,
        List<ApiVersion> apiVersions,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit,
        FunctionType functionType)
        throws Error, TypeManager.Error
    {
        final List<FunctionDescription> functionDescriptions = new ArrayList<FunctionDescription>();

        ListIterator<ApidocTagParser.Item> tagIterator = tags.listIterator();
        while (tagIterator.hasNext())
        {
            final FunctionDescription description = createFunctionFromTags(
                tagIterator,
                typeManager,
                groups,
                urlPrefixReplacements,
                apiVersions,
                requiredFunctionCaptionLenLimit,
                requiredGroupNameLenLimit,
                functionType);
            if (description != null)
                functionDescriptions.add(description);
        }

        return functionDescriptions;
    }

    //---------------------------------------------------------------------------------------------

    private static final class Param
    {
        List<Apidoc.Value> values;
        String structName;
        boolean deprecated = false;
        String deprecatedDescription = "";
        String example = "";
    }

    /**
     * @return Null if the comment should not convert to a Function.
     */
    private FunctionDescription createFunctionFromTags(
        ListIterator<ApidocTagParser.Item> tagIterator,
        TypeManager typeManager,
        List<Apidoc.Group> groups,
        List<Replacement> urlPrefixReplacements,
        List<ApiVersion> apiVersions,
        int requiredFunctionCaptionLenLimit,
        int requiredGroupNameLenLimit,
        FunctionType functionType)
        throws Error, TypeManager.Error
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
        boolean structParsed = false;
        boolean exampleParsed = false;
        boolean subscribeParsed = false;

        FunctionDescription description = null;
        switch (functionType)
        {
            case API:
                description = createFunctionFromApidocItem(
                    item, groups, urlPrefixReplacements, apiVersions);
                break;
            case TRANSACTION:
                description = new FunctionDescription();
                description.function.description = item.getFullText(indentLevel);
                break;
            default:
                throw new IllegalStateException();
        }

        while (tagIterator.hasNext())
        {
            item = tagIterator.next();

            if (TAG_APIDOC.equals(item.getTag()))
            {
                tagIterator.previous(); //< Return previous tag for future parsing.
                break;
            }
            else if (TAG_DEPRECATED.equals(item.getTag()))
            {
                description.function.deprecated =
                    checkTagOnce(item, description.function.deprecated, TAG_DEPRECATED);
                checkNoAttribute(item);
                description.function.deprecatedDescription = item.getFullText(indentLevel);
            }
            else if (TAG_STRUCT.equals(item.getTag()))
            {
                if (description.function.input.type.isParsed())
                {
                    throw new Error(item.getErrorPrefix() +
                        "%apidoc type and %struct can not be both specified.");
                }
                structParsed = checkTagOnce(item, structParsed, TAG_STRUCT);
                if (ATTR_OPT.equals(item.getAttribute()))
                    description.function.input.optional = true;
                else
                    checkNoAttribute(item);
                try
                {
                    description.function.input.type.fillFromName(item.getFullText(indentLevel));
                }
                catch (Exception e)
                {
                    throw new Error(item.getErrorPrefix() + e.getMessage());
                }
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
            else if (TAG_JSONRPC.equals(item.getTag()))
            {
                description.function.jsonrpc.parse(item, indentLevel + 1);
            }
            else if (TAG_PARAM.equals(item.getTag()))
            {
                final Apidoc.Param param = parseParam(
                    item, tagIterator, ParamDirection.Input, ParamMode.WithToken);

                checkDuplicateParam(item, description.function.input.params, param.name);
                if (param.unused)
                    description.function.input.unusedParams.add(param);
                else
                    description.function.input.params.add(param);

                addStructParamsAndDescription(
                    description.function.input.params,
                    description.function.input.unusedParams,
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
            else if (TAG_EXAMPLE.equals(item.getTag()))
            {
                exampleParsed = checkTagOnce(item, exampleParsed, TAG_EXAMPLE);
                checkNoAttribute(item);
                description.function.input.example = item.getFullText(indentLevel).trim();
            }
            else if (!item.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                throwUnknownTag(item);
            }
        }

        if (ApiVersion.shouldPathBeIgnored(
            description.urlPrefix + '/' + description.function.name, apiVersions))
        {
            return null;
        }

        if (requiredFunctionCaptionLenLimit >= 0 && description.function.caption.isEmpty())
            throw new Error(firstItemErrorPrefix + TAG_CAPTION + " unspecified.");
        if (requiredGroupNameLenLimit >= 0 && description.function.groups.isEmpty())
            throw new Error(firstItemErrorPrefix + TAG_INGROUP + " unspecified.");

        return description;
    }

    private void addStructParamsAndDescription(
        List<Apidoc.Param> params,
        List<Apidoc.Param> unusedParams,
        Apidoc.Param param,
        TypeManager typeManager,
        ParamDirection paramDirection)
        throws TypeManager.Error
    {
        if (typeManager == null)
            return;

        final List<Apidoc.Param> structParams =
            typeManager.getStructParams(param.type, param.name, paramDirection);
        for (Apidoc.Param structParam: structParams)
        {
            structParam.isGeneratedFromStruct = true;
            if (structParam.unused)
                unusedParams.add(structParam);
            else
                params.add(structParam);
        }
        if (param.description.isEmpty())
            param.description = typeManager.getStructDescription(param.type);
    }

    /**
     * @return Null if the comment should not convert to a Function.
     */
    private FunctionDescription createFunctionFromApidocItem(
        ApidocTagParser.Item item,
        List<Apidoc.Group> groups,
        List<Replacement> urlPrefixReplacements,
        List<ApiVersion> apiVersions)
        throws Error
    {
        String[] values = Utils.matchRegex(
            functionHeaderRegex, item.getFullText(indentLevel));
        if (values == null)
            throw new Error(item.getErrorPrefix() + "Wrong " + TAG_APIDOC + " function header.");

        for (Replacement r: urlPrefixReplacements)
            values[1] = values[1].replace('/' + r.target + '/', '/' + r.replacement + '/');

        try
        {
            values[1] = ApiVersion.applyExactOrNearestVersionToRange(values[1], apiVersions);
        }
        catch (Exception e)
        {
            throw new Error(item.getErrorPrefix() + e.getMessage());
        }

        FunctionDescription result = new FunctionDescription();
        if (!groups.isEmpty())
        {
            for (Apidoc.Group g: groups)
            {
                if (!g.urlPrefix.isEmpty() && values[1].startsWith(g.urlPrefix + '/'))
                {
                    result.urlPrefix = g.urlPrefix;
                    values[1] = values[1].substring(g.urlPrefix.length());
                    break;
                }
            }
        }
        assert values[1].charAt(0) == '/';
        values[1] = values[1].substring(1); //< Removing initial `/`.

        result.function.method = values[0].trim();
        try
        {
            result.function.name = URLDecoder.decode(values[1], "UTF-8");
        }
        catch (UnsupportedEncodingException e)
        {
            result.function.name = values[1];
        }
        result.function.description = values[2].trim();

        final String label = item.getLabel();
        if (label != null && !label.isEmpty())
        {
            if (LABEL_ARRAY_PARAMS.equals(label))
            {
                result.function.arrayParams = true;
            }
            else
            {
                try
                {
                    result.function.input.type.fillFromLabel(label);
                }
                catch (Exception e)
                {
                    throw new Error(
                        item.getErrorPrefix() + "Invalid function type \"" + label + "\" found.");
                }
            }
        }

        result.function.proprietary = false;
        result.function.input.optional = false;
        final String attribute = item.getAttribute();
        if (attribute != null && !attribute.isEmpty())
        {
            if (ATTR_PROPRIETARY.equals(attribute))
                result.function.proprietary = true;
            else if (ATTR_OPT.equals(attribute))
                result.function.input.optional = true;
            else
                throwInvalidAttribute(item);
        }

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
            param.type.fillFromLabel(item.getLabel());
        }
        catch (Exception e)
        {
            throw new Error(
                item.getErrorPrefix() + "Invalid param type \"" + item.getLabel() + "\" found.");
        }
        Param paramDescription = parseParamItems(tagIterator);
        param.values.addAll(paramDescription.values);
        if (paramDescription.structName != null && !paramDescription.structName.isEmpty())
        {
            if ((param.type.fixed != Apidoc.Type.OBJECT
                    && param.type.fixed != Apidoc.Type.ARRAY
                    && param.type.fixed != Apidoc.Type.UNKNOWN)
                || (param.type.name != null && !param.type.name.isEmpty()))
            {
                throw new Error(item.getErrorPrefix() + "Param `" + param.name +
                    "` can not have %struct tag as it has a type specified.");
            }
            param.type.name = paramDescription.structName;
        }
        param.deprecated = paramDescription.deprecated;
        param.deprecatedDescription = paramDescription.deprecatedDescription;
        param.example = paramDescription.example;

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
        param.proprietary = false;
        param.optional = false;
        param.readonly = false;
        param.unused = false;

        if (ATTR_PROPRIETARY.equals(item.getAttribute()))
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
        else if (ATTR_IMMUTABLE.equals(item.getAttribute()))
        {
            param.immutable = true;
        }
        else if (!"".equals(item.getAttribute()))
        {
            throwInvalidAttribute(item);
        }
    }

    private Param parseParamItems(ListIterator<ApidocTagParser.Item> itemIterator) throws Error
    {
        indentLevel++;
        final Param paramDescription = new Param();
        paramDescription.values = new ArrayList<Apidoc.Value>();

        while (itemIterator.hasNext())
        {
            final ApidocTagParser.Item item = itemIterator.next();

            if (TAG_DEPRECATED.equals(item.getTag()))
            {
                paramDescription.deprecated = true;
                paramDescription.deprecatedDescription = item.getFullText(indentLevel);
            }
            else if (TAG_VALUE.equals(item.getTag()))
            {
                Apidoc.Value value = parseValue(item, itemIterator);
                paramDescription.values.add(value);
            }
            else if (TAG_STRUCT.equals(item.getTag()))
            {
                paramDescription.structName = item.getFullText(indentLevel);
            }
            else if (TAG_EXAMPLE.equals(item.getTag()))
            {
                paramDescription.example = item.getFullText(indentLevel);
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

    private Apidoc.Value parseValue(
        ApidocTagParser.Item valueItem,
        ListIterator<ApidocTagParser.Item> itemIterator) throws Error
    {
        Apidoc.Value value = new Apidoc.Value();
        value.setName(getInitialToken(valueItem, ParamMode.WithToken));
        value.description = valueItem.getTextAfterInitialToken(indentLevel);

        if (ATTR_PROPRIETARY.equals(valueItem.getAttribute()))
        {
            value.proprietary = true;
        }
        else if (ATTR_UNUSED.equals(valueItem.getAttribute()))
        {
            value.unused = true;
        }
        else if (!valueItem.getAttribute().isEmpty())
        {
            throw new Error(valueItem.getErrorPrefix() + "unexpected attribute \""
                + valueItem.getAttribute() + "\".");
        }

        while (itemIterator.hasNext())
        {
            ApidocTagParser.Item item = itemIterator.next();
            if (TAG_DEPRECATED.equals(item.getTag()))
            {
                value.deprecated = true;
                value.deprecatedDescription = item.getFullText(indentLevel);
            }
            else if (!item.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                itemIterator.previous(); //< Return previous item for future parsing.
                break;
            }
        }
        return value;
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
        param.type.fixed = Apidoc.Type.ENUM;
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
        throws Error, TypeManager.Error
    {
        assert TAG_RETURN.equals(item.getTag());
        indentLevel++;
        checkNoAttribute(item);
        Apidoc.Result result = new Apidoc.Result();
        result.caption = item.getFullText(indentLevel);
        try
        {
            result.type.fillFromLabel(item.getLabel());
        }
        catch (Exception e)
        {
            throw new Error(item.getErrorPrefix() +
                "Invalid result type `" + item.getLabel() + "`: " + e.getMessage());
        }

        boolean deprecatedAttributeTagFound = false;
        boolean exampleParsed = false;
        boolean structParsed = false;
        while (tagIterator.hasNext())
        {
            item = tagIterator.next();
            if (TAG_STRUCT.equals(item.getTag()))
            {
                if ((result.type.fixed != Apidoc.Type.OBJECT
                    && result.type.fixed != Apidoc.Type.ARRAY
                    && result.type.fixed != Apidoc.Type.UNKNOWN)
                    || (result.type.name != null && !result.type.name.isEmpty()))
                {
                    throw new Error(item.getErrorPrefix() +
                        "%return type and %struct can not be both specified.");
                }
                structParsed = checkTagOnce(item, structParsed, TAG_STRUCT);
                try
                {
                    result.type.fillFromName(item.getFullText(indentLevel));
                }
                catch (Exception e)
                {
                    throw new Error(item.getErrorPrefix() + e.getMessage());
                }
            }
            else if (TAG_PARAM.equals(item.getTag()))
            {
                Apidoc.Param param =
                    parseParam(item, tagIterator, ParamDirection.Output, ParamMode.WithToken);

                checkDuplicateParam(item, result.params, param.name);
                if (param.unused)
                    result.unusedParams.add(param);
                else
                    result.params.add(param);

                addStructParamsAndDescription(
                    result.params,
                    result.unusedParams,
                    param,
                    typeManager,
                    ParamDirection.Output);
            }
            else if (TAG_EXAMPLE.equals(item.getTag()))
            {
                exampleParsed = checkTagOnce(item, exampleParsed, TAG_EXAMPLE);
                checkNoAttribute(item);
                result.example = item.getFullText(indentLevel).trim();
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
        else if (ATTR_IMMUTABLE.equals(tag.getAttribute()))
            param.immutable = true;
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
        "\\s*([A-Z]+)\\s+(/[\\w{}./%?-]*)(?:\\s+(.*))?", Pattern.DOTALL);
    //       0Method     1Path                  2Txt
    //        GET         /ec2/getUsers        \nReturn users registered in the System.
}
