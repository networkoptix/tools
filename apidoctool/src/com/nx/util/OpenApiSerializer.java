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

    public static String toString(Apidoc apidoc)
    {
        if (apidoc.groups.isEmpty())
            return "";
        final JSONObject root = new JSONObject();
        root.put("openapi", "3.0.2");
        final JSONObject info = getObject(root, "info");
        info.put("title", "Nx VMS API");
        info.put("version", "1.0.0");
        final JSONObject url = new JSONObject();
        url.put("url", "/");
        getArray(root, "servers").put(url);
        final JSONArray tags = getArray(root, "tags");
        final HashSet<String> usedTags = new HashSet<String>();
        for (final Apidoc.Group group: apidoc.groups)
        {
            if (!group.urlPrefix.equals("/rest"))
                continue;
            if (!fillPaths(getObject(root, "paths"), group))
                continue;
            if (!usedTags.contains(group.groupName))
            {
                usedTags.add(group.groupName);
                JSONObject tag = new JSONObject();
                tag.put("name", group.groupName);
                tag.put("description", group.groupDescription);
                tags.put(tag);
            }
        }
        return root.toString(2);
    }

    private static boolean fillPaths(JSONObject paths, Apidoc.Group group)
    {
        boolean filled = false;
        for (final Apidoc.Function function: group.functions)
        {
            if (function.method.isEmpty())
                continue;
            final JSONObject path = getObject(paths, group.urlPrefix + "/" + function.name);
            final JSONObject method = fillPath(path, function);
            final JSONArray tags = getArray(method, "tags");
            tags.put(group.groupName);
            filled = true;
        }
        return filled;
    }

    private static JSONObject fillPath(JSONObject path, Apidoc.Function function)
    {
        final JSONObject method = getObject(path, function.method.toLowerCase());
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
            if (param.isGeneratedFromStruct)
            {
                final JSONObject requestBody = getObject(method, "requestBody");
                requestBody.put("required", true);
                final JSONObject schema = getObject(getObject(getObject(
                    requestBody, "content"), "application/json"), "schema");
                addStructParam(schema, param);
                continue;
            }
            final JSONObject parameter = toJson(param);
            if (parameter == null)
                continue;
            parameter.put("in", "query");
            getArray(method, "parameters").put(parameter);
        }
        fillResult(method, function.result);
        return method;
    }

    private static void fillResult(JSONObject path, Apidoc.Result result)
    {
        final JSONObject default_ = getObject(getObject(path, "responses"), "default");
        default_.put("description", result.caption);
        if (result.type == Apidoc.Type.UNKNOWN)
            return;
        JSONObject schema = getObject(getObject(getObject(
            default_, "content"), "application/json"), "schema");
        String type = toString(result.type);
        schema.put("type", type);
        if (type.equals("array"))
        {
            schema = getObject(schema, "items");
            type = (result.type == Apidoc.Type.ARRAY) ? "object" : "string";
            schema.put("type", type);
            if (result.type == Apidoc.Type.UUID_ARRAY)
                schema.put("format", "uuid");
        }
        if (type.equals("object"))
        {
            for (final Apidoc.Param param: result.params)
                addStructParam(schema, param);
        }
    }

    private static void fillSchemaType(JSONObject schema, Apidoc.Param param)
    {
        final String type = toString(param.type);
        schema.put("type", type);
        if (type.equals("array"))
        {
            final JSONObject items = getObject(schema, "items");
            items.put("type", (param.type == Apidoc.Type.ARRAY) ? "object" : "string");
            if (param.type == Apidoc.Type.UUID_ARRAY)
                items.put("format", "uuid");
        }
        if (param.type == Apidoc.Type.ENUM)
        {
            if (!param.values.isEmpty())
            {
                final JSONArray enum_ = getArray(schema, "enum");
                for (final Apidoc.Value value: param.values)
                    enum_.put(value.name);
            }
        }
        else if (param.type == Apidoc.Type.UUID)
        {
            schema.put("format", "uuid");
        }
    }

    private static void addStructParam(JSONObject schema, Apidoc.Param param)
    {
        if (param.proprietary)
            return;
        final JSONObject parameter = getParamByPath(schema, param.name);
        if (param.description != null && !param.description.isEmpty())
            parameter.put("description", param.description);
        if (param.readonly)
            parameter.put("readOnly", true);
        if (!param.optional)
            setRequired(schema, param.name);
        fillSchemaType(parameter, param);
    }

    private static JSONObject toJson(Apidoc.Param param)
    {
        if (param.proprietary)
            return null;
        final JSONObject result = new JSONObject();
        result.put("name", param.name);
        if (param.description != null && !param.description.isEmpty())
            result.put("description", param.description);
        if (param.readonly)
            result.put("readOnly", true);
        else if (!param.optional)
            result.put("required", true);
        fillSchemaType(getObject(result, "schema"), param);
        return result;
    }

    private static String toString(Apidoc.Type type)
    {
        if (type == Apidoc.Type.FLOAT)
            return "number";
        if (type == Apidoc.Type.FLAGS)
            return "integer";
        if (type == Apidoc.Type.STRING_ARRAY
            || type == Apidoc.Type.UUID_ARRAY
            || type == Apidoc.Type.ARRAY_JSON)
        {
            return "array";
        }
        if (type != Apidoc.Type.BOOLEAN
            && type != Apidoc.Type.INTEGER
            && type != Apidoc.Type.OBJECT
            && type != Apidoc.Type.ARRAY)
        {
            return "string";
        }
        return type.toString();
    }
}
