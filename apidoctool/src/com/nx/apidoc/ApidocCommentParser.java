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
        public String outputStructName;
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

    /**
     * @return Empty list if the comment should not convert to an XML function.
     */
    public List<FunctionDescription> createFunctionsFromTags(
        List<ApidocTagParser.Item> tags, TypeManager typeManager)
        throws Error,
        TypeManager.Error

    {
        final List<FunctionDescription> functions = new ArrayList<FunctionDescription>();

        ListIterator<ApidocTagParser.Item> tagIterator = tags.listIterator();
        while (tagIterator.hasNext())
            functions.add(createFunctionFromTags(tagIterator, typeManager));

        return functions;
    }

    private final class Result
    {
        Apidoc.Result result;
        String outputStructName;
    }

    private final class Param
    {
        List<Apidoc.Value> values;
        String structName;
    }

    //---------------------------------------------------------------------------------------------

    /**
     * @return Null if the comment should not convert to an XML function.
     */
    private FunctionDescription createFunctionFromTags(
        ListIterator<ApidocTagParser.Item> tagIterator, TypeManager typeManager)
        throws Error,
        TypeManager.Error
    {
        ApidocTagParser.Item item = tagIterator.next();

        if (!TAG_APIDOC.equals(item.getTag()))
        {
            throw new Error(item.getErrorPrefix() +
                "Comment should start with " + TAG_APIDOC + " tag.");
        }

        FunctionDescription description = createFunctionFromApidocItem(item);

        boolean captionParsed = false;
        boolean permissionsParsed = false;
        boolean returnParsed = false;
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
            }
            else if (TAG_CAPTION.equals(item.getTag()))
            {
                captionParsed = checkTagOnce(item, captionParsed, TAG_CAPTION);
                checkNoAttribute(item);
                description.function.caption = item.getFullText(indentLevel);
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
                final Result resultDescription = parseFunctionResult(
                    item, tagIterator, typeManager);
                description.function.result = resultDescription.result;
                description.outputStructName = resultDescription.outputStructName;
            }
            else if (!item.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                throwUnknownTag(item);
            }
        }

        return description;
    }

    private void addStructParams(
        List<Apidoc.Param> params,
        List<Apidoc.Param> unusedParams,
        Apidoc.Param param,
        TypeManager typeManager,
        ParamDirection direction)
        throws TypeManager.Error
    {
        if (typeManager != null && param.structName != null)
        {
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

        result.function.name = values[2];
        result.function.method = values[0].trim();
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
        Param paramDescription = parseParamTags(tagIterator);
        param.values.addAll(paramDescription.values);
        param.structName = paramDescription.structName;

        if (paramDirection == ParamDirection.Output)
            parseFunctionResultParamAttr(item, param);
        else
            parseFunctionParamAttr(item, param);

        indentLevel -= paramIndentLevel;
        return param;
    }

    private void parseFunctionParamAttr(ApidocTagParser.Item item, Apidoc.Param param)
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
        else if (ATTR_UNUSED.equals(item.getAttribute()))
        {
            param.unused = true;
        }
        else
        {
            throwInvalidAttribute(item);
        }
    }

    private Param parseParamTags(
        ListIterator<ApidocTagParser.Item> tagIterator)
        throws Error
    {
        indentLevel++;
        final Param paramDescription = new Param();
        paramDescription.values = new ArrayList<Apidoc.Value>();
        while (tagIterator.hasNext())
        {
            final ApidocTagParser.Item tag = tagIterator.next();
            if (TAG_VALUE.equals(tag.getTag()))
            {
                // ATTENTION: Currently, [proprietary] params are ignored, until supported in XML.
                if (ATTR_PROPRIETARY.equals(tag.getAttribute()))
                    continue;

                checkNoAttribute(tag);
                Apidoc.Value value = new Apidoc.Value();
                value.name = getInitialToken(tag, ParamMode.WithToken);
                value.description = tag.getTextAfterInitialToken(indentLevel);
                paramDescription.values.add(value);
            }
            else if (TAG_STRUCT.equals(tag.getTag()))
            {
                paramDescription.structName = tag.getFullText(indentLevel);
            }
            else if (!tag.getTag().startsWith(TAG_COMMENTED_OUT))
            {
                tagIterator.previous(); //< Return previous tag for future parsing.
                break;
            }
        }
        indentLevel--;
        return paramDescription;
    }

    private void fillDefaultFormatParam(ApidocTagParser.Item item, Apidoc.Param param)
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

    private Result parseFunctionResult(
        ApidocTagParser.Item item,
        ListIterator<ApidocTagParser.Item> tagIterator,
        TypeManager typeManager)
        throws Error,
        TypeManager.Error
    {
        assert TAG_RETURN.equals(item.getTag());
        indentLevel++;
        checkNoAttribute(item);
        Result resultDescription = new Result();
        resultDescription.result = new Apidoc.Result();
        resultDescription.result.caption = item.getFullText(indentLevel);
        try
        {
            resultDescription.result.type = Apidoc.Type.fromString(item.getLabel());
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
                resultDescription.outputStructName = item.getFullText(indentLevel);
            }
            else if (TAG_PARAM.equals(item.getTag()))
            {
                Apidoc.Param param = parseParam(
                    item, tagIterator, ParamDirection.Output, ParamMode.WithToken);

                checkDuplicateParam(item, resultDescription.result.params, param.name);
                if (param.unused)
                    resultDescription.result.unusedParams.add(param);
                else
                    resultDescription.result.params.add(param);

                addStructParams(
                    resultDescription.result.params,
                    resultDescription.result.unusedParams,
                    param,
                    typeManager,
                    ParamDirection.Output);
            }
            else if ("%attribute".equals(item.getTag()))
            {
                // Support for old deprecated Apidoc Comment format which has
                // "%attribute" tags following "%result" instead of "%param".
                deprecatedAttributeTagFound = true;
                parseFunctionResultAttributeDeprecated(item, resultDescription.result);
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
        return resultDescription;
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
        param.optional = false;
        if ("".equals(tag.getAttribute()))
            param.proprietary = false;
        else if (ATTR_PROPRIETARY.equals(tag.getAttribute()))
            param.proprietary = true;
        else if (ATTR_UNUSED.equals(tag.getAttribute()))
            param.unused = true;
        else
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

    private void throwInvalidAttribute(ApidocTagParser.Item item)
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

    private void checkDuplicateParam(
        ApidocTagParser.Item item, List<Apidoc.Param> params, String paramName)
        throws Error
    {
        // Overwrite param that generated by %struct tag
        Iterator<Apidoc.Param> iterator = params.iterator();
        while (iterator.hasNext()) {
            Apidoc.Param existingParam = iterator.next();
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
        "\\s*([A-Z]+ )?\\s*(?:(/\\w+)/)?([\\w/]+)(.*)", Pattern.DOTALL);
      //     0HttpMthd        1UrlPre   2FnNm      3Txt
      //       GET             /ec2     getRe      \nRe
}
