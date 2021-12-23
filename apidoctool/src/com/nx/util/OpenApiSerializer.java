package com.nx.util;

import java.util.HashSet;

import org.json.JSONArray;
import org.json.JSONObject;

import com.nx.apidoc.Apidoc;

public final class OpenApiSerializer
{
    private static JSONObject getObject(JSONObject object, String key)
    {
        JSONObject value = object.optJSONObject(key);
        if (value == null)
        {
            value = new JSONObject();
            object.put(key, value);
        }
        return value;
    }

    private static JSONArray getArray(JSONObject object, String key)
    {
        JSONArray value = object.optJSONArray(key);
        if (value == null)
        {
            value = new JSONArray();
            object.put(key, value);
        }
        return value;
    }

    private static JSONObject getParamByPath(JSONObject schema, String path)
    {
        if (!schema.has("type"))
            schema.put("type", "object");
        schema = getObject(schema, "properties");
        final int subpathPos = path.indexOf('.');
        String item = (subpathPos < 0) ? path : path.substring(0, subpathPos);
        path = (subpathPos < 0) ? "" : path.substring(subpathPos + 1);
        if (item.endsWith("[]"))
        {
            item = item.substring(0, item.length() - 2);
            if (!path.isEmpty())
                schema = getObject(getObject(schema, item), "items");
        }
        else
        {
            if (!path.isEmpty())
                schema = getObject(schema, item);
        }
        if (!path.isEmpty())
            return getParamByPath(schema, path);
        return getObject(schema, item);
    }

    private static void setRequired(JSONObject schema, String path)
    {
        final int subpathPos = path.indexOf('.');
        String item = (subpathPos < 0) ? path : path.substring(0, subpathPos);
        path = (subpathPos < 0) ? "" : path.substring(subpathPos + 1);
        if (item.endsWith("[]"))
        {
            item = item.substring(0, item.length() - 2);
            if (!path.isEmpty())
                schema = getObject(getObject(getObject(schema, "properties"), item), "items");
        }
        else
        {
            if (!path.isEmpty())
                schema = getObject(getObject(schema, "properties"), item);
        }
        if (!path.isEmpty())
            setRequired(schema, path);
        else
            getArray(schema, "required").put(item);
    }

    public static String toString(
        Apidoc apidoc,
        JSONObject root,
        int requiredGroupNameLenLimit,
        boolean generateOrderByParameters) throws Exception
    {
        if (apidoc.groups.isEmpty())
            return "";
        final JSONArray tags = getArray(root, "tags");
        final JSONObject refParameters = getObject(getObject(root, "components"), "parameters");
        final HashSet<String> usedTags = new HashSet<String>();
        for (final Apidoc.Group group: apidoc.groups)
        {
            if (!fillPaths(
                getObject(root, "paths"), group, refParameters, generateOrderByParameters))
            {
                continue;
            }
            JSONObject tag = null;
            for (int i = 0; i < tags.length(); ++i)
            {
                tag = tags.optJSONObject(i);
                if (tag != null && tag.optString("name", "").equals(group.groupName))
                {
                    usedTags.add(group.groupName);
                    break;
                }
                tag = null;
            }
            if (tag == null)
            {
                if (requiredGroupNameLenLimit >= 0)
                {
                    throw new Exception(
                        "No predefined tag \"" + group.groupName + "\" in Open API template.");
                }
                tag = new JSONObject();
                tag.put("name", group.groupName);
                tag.put("description", Utils.cleanupDescription(group.groupDescription));
                tags.put(tag);
            }
            if (requiredGroupNameLenLimit > 0 && group.groupName.length() > requiredGroupNameLenLimit)
                throw new Exception("Tag \"" + group.groupName + "\" is too long.");
        }
        if (requiredGroupNameLenLimit >= 0)
        {
            for (int i = 0; i < tags.length(); ++i)
            {
                final JSONObject tag = tags.optJSONObject(i);
                if (tag != null)
                {
                    final String tagName = tag.optString("name", "");
                    if (!tagName.isEmpty() && !usedTags.contains(tagName))
                        throw new Exception("Unused tag \"" + tagName + "\" in Open API template.");
                }
            }
        }
        return root.toString(2);
    }

    private static boolean fillPaths(
        JSONObject paths,
        Apidoc.Group group,
        JSONObject refParameters,
        boolean generateOrderByParameters) throws Exception
    {
        boolean filled = false;
        for (final Apidoc.Function function: group.functions)
        {
            final JSONObject path = getObject(paths, group.urlPrefix + "/" + function.name);
            final JSONObject method = fillPath(path, function, refParameters, generateOrderByParameters);
            final JSONArray tags = getArray(method, "tags");
            tags.put(group.groupName);
            filled = true;
        }
        return filled;
    }

    private static JSONObject fillPath(
        JSONObject path,
        Apidoc.Function function,
        JSONObject refParameters,
        boolean generateOrderByParameters) throws Exception
    {
        final JSONObject method = getObject(path, function.knownMethod());
        if (!function.caption.isEmpty())
            method.put("summary", function.caption);
        final String description = (function.proprietary ? "<p><b>Proprietary.</b></p>" : "")
            + Utils.cleanupDescription(function.description);
        if (!description.isEmpty())
            method.put("description", description);
        if (function.permissions != null && !function.permissions.isEmpty())
            method.put("x-permissions", function.permissions);
        for (final Apidoc.Param param: function.params)
        {
            final boolean inPath = function.name.indexOf("{" + param.name + "}") >= 0;
            if (inPath)
            {
                final JSONObject parameter = toJson(param);
                parameter.put("in", "path");
                parameter.remove("readOnly");
                parameter.put("required", true);
                getArray(method, "parameters").put(parameter);
                continue;
            }
            if (function.areInBodyParameters())
            {
                final JSONObject requestBody = getObject(method, "requestBody");
                if (!param.optional)
                    requestBody.put("required", true);
                final JSONObject schema = getObject(getObject(getObject(
                    requestBody, "content"), "application/json"), "schema");
                addStructParam(schema, param);
                continue;
            }
            JSONObject parameter;
            if (param.isRef)
            {
                if (!refParameters.has(param.name))
                    throw new Exception("Ref parameter '" + param.name + "' is missed");
                parameter = new JSONObject();
                parameter.put("$ref", "#/components/parameters/" + param.name);
            }
            else
            {
                parameter = toJson(param);
                if (parameter == null)
                    continue;
                parameter.put("in", "query");
            }
            getArray(method, "parameters").put(parameter);
        }
        fillResult(method, function.result, generateOrderByParameters);
        return method;
    }

    private static JSONObject orderByTemplate()
    {
        JSONObject result = new JSONObject();
        result.put("name", "_orderBy");
        JSONObject schema = getObject(result, "schema");
        schema.put("type", "array");
        getObject(schema, "items").put("type", "string");
        result.put("in", "query");
        return result;
    }

    private static JSONObject fillOrderBy(JSONObject orderBy, Apidoc.Param param)
    {
        if (param.type == Apidoc.Type.ARRAY
            || param.type == Apidoc.Type.STRING_ARRAY
            || param.type == Apidoc.Type.UUID_ARRAY
            || param.type == Apidoc.Type.OBJECT)
        {
            return orderBy;
        }
        final int lastCharOfArrayName = param.name.lastIndexOf("[]");
        if (orderBy != null || lastCharOfArrayName != -1)
        {
            if (orderBy == null)
                orderBy = orderByTemplate();
            final String arrayName = (lastCharOfArrayName == -1)
                ? ""
                : param.name.substring(0, lastCharOfArrayName);
            final JSONObject schema = orderBy.getJSONObject("schema");
            final JSONArray enum_ = getArray(schema.getJSONObject("items"), "enum");
            boolean isFirstArrayItem = true;
            for (int i = enum_.length() - 1; i >= 0 && isFirstArrayItem; --i)
            {
                if (enum_.getString(i).startsWith(arrayName))
                    isFirstArrayItem = false;
            }
            enum_.put(param.name);
            if (isFirstArrayItem)
                getArray(schema, "default").put(param.name);
        }
        return orderBy;
    }

    private static void fillResult(
        JSONObject path, Apidoc.Result result, boolean generateOrderByParameters) throws Exception
    {
        final JSONObject default_ = getObject(getObject(path, "responses"), "default");
        default_.put("description", Utils.cleanupDescription(result.caption));
        if (result.type == Apidoc.Type.UNKNOWN)
            return;
        JSONObject schema = getObject(getObject(getObject(
            default_, "content"), "application/json"), "schema");
        fillSchemaType(schema, result.type);
        if (result.type == Apidoc.Type.ARRAY || result.type == Apidoc.Type.OBJECT)
        {
            JSONObject orderBy = null;
            if (result.type == Apidoc.Type.ARRAY)
            {
                schema = schema.getJSONObject("items");
                if (generateOrderByParameters)
                    orderBy = orderByTemplate();
            }
            for (final Apidoc.Param param: result.params)
            {
                addStructParam(schema, param);
                if (generateOrderByParameters)
                    orderBy = fillOrderBy(orderBy, param);
            }
            if (orderBy != null)
                getArray(path, "parameters").put(orderBy);
        }
    }

    private static void fillSchemaType(JSONObject schema, Apidoc.Type type)
    {
        switch (type)
        {
            case UNKNOWN:
            case OBJECT_JSON:
            case ARRAY_JSON:
            case TEXT:
            case ANY:
                break;
            case STRING:
            case ENUM:
            case FLAGS:
                schema.put("type", "string");
                break;
            case OPTION:
                schema.put("enum", getArray(schema, "enum").put("true"));
            case BOOLEAN:
                schema.put("type", "boolean");
                break;
            case INTEGER:
                schema.put("type", "integer");
                break;
            case FLOAT:
                schema.put("type", "number");
                break;
            case UUID:
                schema.put("type", "string");
                schema.put("format", "uuid");
                break;
            case OBJECT:
                schema.put("type", "object");
                break;
            case ARRAY:
                schema.put("type", "array");
                getObject(schema, "items").put("type", "object");
                break;
            case STRING_ARRAY:
                schema.put("type", "array");
                getObject(schema, "items").put("type", "string");
                break;
            case UUID_ARRAY:
                schema.put("type", "array");
                schema = getObject(schema, "items");
                schema.put("type", "string");
                schema.put("format", "uuid");
                break;
            case BASE64:
                schema.put("type", "string");
                schema.put("format", "byte");
                break;
            case BINARY:
                schema.put("type", "string");
                schema.put("format", "binary");
                break;
            default:
                assert false: "Unspecified schema type.";
        }
    }

    private static void fillSchemaType(JSONObject schema, Apidoc.Param param)
    {
        fillSchemaType(schema, param.type);
        if (param.type == Apidoc.Type.ENUM || param.type == Apidoc.Type.FLAGS)
        {
            if (param.values.isEmpty())
                return;
            final JSONArray enum_ = getArray(schema, "enum");
            for (final Apidoc.Value value: param.values)
                enum_.put(value.name);
        }
    }

    private static String description(Apidoc.Param param) throws Exception
    {
        String result = param.proprietary ? "<b>Proprietary.</b>" : "";
        String cleanedDescription = Utils.cleanupDescription(param.description);
        if (!cleanedDescription.isEmpty())
            result += (param.proprietary ? " " : "") + cleanedDescription;
        if (param.values.isEmpty())
            return result;
        if (param.type == Apidoc.Type.BOOLEAN
            || param.type == Apidoc.Type.ENUM
            || param.type == Apidoc.Type.FLAGS)
        {
            boolean hasDescription = false;
            for (final Apidoc.Value value: param.values)
            {
                if (value.description != null && !value.description.trim().isEmpty())
                {
                    hasDescription = true;
                    break;
                }
            }
            if (!hasDescription)
                return result;
        }
        if (!result.isEmpty())
            result += "\n\n";
        if (param.type == Apidoc.Type.FLAGS)
            result += "Possible values are one of or the combination by `|` of the following:";
        else
            result += "Possible values are:";
        for (final Apidoc.Value value: param.values)
        {
            result += "\n- `" + value.nameForDescription(param.type) + '`';
            if (value.description == null)
                continue;
            final String description = value.description.trim();
            if (!description.isEmpty())
                result += ' ' + description;
        }
        return result;
    }

    private static void putDescription(Apidoc.Param param, JSONObject object) throws Exception
    {
        String result = description(param);
        if (!result.isEmpty())
            object.put("description", result);
    }

    private static void addStructParam(JSONObject schema, Apidoc.Param param) throws Exception
    {
        final JSONObject parameter = getParamByPath(schema, param.name);
        putDescription(param, parameter);
        if (param.readonly)
            parameter.put("readOnly", true);
        if (!param.optional)
            setRequired(schema, param.name);
        fillSchemaType(parameter, param);
    }

    private static JSONObject toJson(Apidoc.Param param) throws Exception
    {
        final JSONObject result = new JSONObject();
        result.put("name", param.name);
        putDescription(param, result);
        if (param.readonly)
            result.put("readOnly", true);
        else if (!param.optional)
            result.put("required", true);
        fillSchemaType(getObject(result, "schema"), param);
        return result;
    }
}
