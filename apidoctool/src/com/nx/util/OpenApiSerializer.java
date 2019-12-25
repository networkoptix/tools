package com.nx.util;

import org.json.JSONArray;
import org.json.JSONObject;

import com.nx.apidoc.Apidoc;

public final class OpenApiSerializer
{
    private static JSONObject getObject(JSONObject from, final String key)
    {
        JSONObject value = from.optJSONObject(key);
        if (value == null)
        {
            value = new JSONObject();
            from.put(key, value);
        }
        return value;
    }

    private static JSONArray getArray(JSONObject from, final String key)
    {
        JSONArray value = from.optJSONArray(key);
        if (value == null)
        {
            value = new JSONArray();
            from.put(key, value);
        }
        return value;
    }

    private static JSONObject getParamByPath(JSONObject schema, String path)
    {
        schema = getObject(schema, "properties");
        final int subpathPos = path.indexOf('.');
        String item = subpathPos < 0 ? path : path.substring(0, subpathPos);
        path = subpathPos < 0 ? "" : path.substring(subpathPos + 1);
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
        String item = subpathPos < 0 ? path : path.substring(0, subpathPos);
        path = subpathPos < 0 ? "" : path.substring(subpathPos + 1);
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

    public static String toString(final Apidoc apidoc)
    {
        if (apidoc.groups.isEmpty())
            return "";
        JSONObject root = new JSONObject();
        root.put("openapi", "3.0.0");
        JSONObject info = getObject(root, "info");
        info.put("title", "Nx VMS API");
        info.put("version", "2.0.0");
        JSONObject url = new JSONObject();
        url.put("url", "https://localhost:7001");
        getArray(root, "servers").put(url);
        for (final Apidoc.Group group: apidoc.groups)
        {
            if (!group.urlPrefix.equals("/rest"))
                continue;
            fillPaths(getObject(root, "paths"), group);
        }
        return root.toString(2);
    }

    private static void fillPaths(JSONObject paths, final Apidoc.Group group)
    {
        for (final Apidoc.Function function: group.functions)
        {
            if (function.method.isEmpty())
                continue;
            JSONObject path = getObject(paths, group.urlPrefix + "/" + function.name);
            fillPath(path, function);
        }
    }

    private static void fillPath(JSONObject path, final Apidoc.Function function)
    {
        JSONObject method = getObject(path, function.method.toLowerCase());
        for (final Apidoc.Param param: function.params)
        {
            final boolean inPath = function.name.indexOf("{" + param.name + "}") >= 0;
            if (!inPath && !method.equals("get") && !method.equals("delete") && param.readonly)
                continue;
            if (inPath)
            {
                JSONObject parameter = toJson(param);
                parameter.put("in", "path");
                parameter.remove("readOnly");
                parameter.put("required", true);
                getArray(method,"parameters").put(parameter);
                continue;
            }
            if (param.isGeneratedFromStruct)
            {
                JSONObject requestBody = getObject(method, "requestBody");
                requestBody.put("required", true);
                JSONObject schema = getObject(getObject(getObject(
                    requestBody, "content"), "application/json"), "schema");
                addStructParam(schema, param);
                continue;
            }
            JSONObject parameter = toJson(param);
            if (parameter == null)
                continue;
            parameter.put("in", "query");
            getArray(method,"parameters").put(parameter);
        }
        fillResult(method, function.result);
    }

    private static void fillResult(JSONObject path, final Apidoc.Result result)
    {
        JSONObject default_ = getObject(getObject(path, "responses"), "default");
        String description = result.caption.isEmpty() ? "none" : result.caption;
        description = description.replace('\n', ' ').replace('"', '\'');
        default_.put("description", description);
        JSONObject schema = getObject(getObject(getObject(
                default_, "content"), "application/json"), "schema");
        String type = toString(result.type);
        schema.put("type", type);
        if (type.equals("array"))
        {
            schema = getObject(schema, "items");
            type = result.type == Apidoc.Type.ARRAY ? "object" : "string";
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

    private static void fillSchemaType(JSONObject schema, final Apidoc.Param param)
    {
        final String type = toString(param.type);
        schema.put("type", type);
        if (type.equals("array"))
        {
            JSONObject items = getObject(schema, "items");
            items.put("type", param.type == Apidoc.Type.ARRAY ? "object" : "string");
            if (param.type == Apidoc.Type.UUID_ARRAY)
                items.put("format", "uuid");
        }
        if (param.type == Apidoc.Type.ENUM)
        {
            if (!param.values.isEmpty())
            {
                JSONArray enum_ = getArray(schema, "enum");
                for (Apidoc.Value value: param.values)
                    enum_.put(value.name);
            }
        }
        else if (param.type == Apidoc.Type.UUID)
        {
            schema.put("format", "uuid");
        }
    }

    private static void addStructParam(JSONObject schema, final Apidoc.Param param)
    {
        if (param.proprietary)
            return;
        JSONObject parameter = getParamByPath(schema, param.name);
        if (param.description != null && !param.description.isEmpty())
        {
            String description = param.description.replace('\n', ' ').replace('"', '\'');
            parameter.put("description", description);
        }
        if (param.readonly)
            parameter.put("readOnly", true);
        if (!param.optional)
            setRequired(schema, param.name);
        fillSchemaType(parameter, param);
    }

    private static JSONObject toJson(final Apidoc.Param param)
    {
        if (param.proprietary)
            return null;
        JSONObject result = new JSONObject();
        result.put("name", param.name);
        if (param.description != null && !param.description.isEmpty())
        {
            String description = param.description.replace('\n', ' ').replace('"', '\'');
            result.put("description", description);
        }
        if (param.readonly)
            result.put("readOnly", true);
        else if (!param.optional)
            result.put("required", true);
        fillSchemaType(getObject(result, "schema"), param);
        return result;
    }

    private static String toString(final Apidoc.Type type)
    {
        if (type == Apidoc.Type.FLOAT)
            return "number";
        if (type == Apidoc.Type.FLAGS)
            return "integer";
        if (
                type != Apidoc.Type.BOOLEAN &&
                type != Apidoc.Type.INTEGER &&
                type != Apidoc.Type.OBJECT &&
                type != Apidoc.Type.ARRAY
            )
        {
            if (
                    type == Apidoc.Type.STRING_ARRAY ||
                    type == Apidoc.Type.UUID_ARRAY ||
                    type == Apidoc.Type.ARRAY_JSON
                )
            {
                return "array";
            }
            return "string";
        }
        return type.toString();
    }
}
