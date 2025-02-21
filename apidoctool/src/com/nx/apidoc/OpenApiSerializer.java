// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import java.util.HashSet;

import com.nx.utils.Utils;
import org.json.JSONArray;
import org.json.JSONObject;

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
        final int subpathPos = path.indexOf('.');
        String item = (subpathPos < 0) ? path : path.substring(0, subpathPos);
        path = (subpathPos < 0) ? "" : path.substring(subpathPos + 1);
        if (item.startsWith("#"))
        {
            schema = oneOfSchema(schema, item);
            if (path.isEmpty())
                return schema;
            return getParamByPath(schema, path);
        }
        if (!schema.has("type"))
            schema.put("type", "object");
        if (item.startsWith(TypeInfo.mapKeyPlaceholder))
        {
            schema = additionalPropertiesSchema(schema, item);
            if (path.isEmpty())
                return schema;
            return getParamByPath(schema, path);
        }
        schema = getObject(schema, "properties");
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
        if (item.startsWith("#"))
        {
            schema = oneOfSchema(schema, item);
            if (!path.isEmpty())
                setRequired(schema, path);
            return;
        }
        if (item.startsWith(TypeInfo.mapKeyPlaceholder))
        {
            schema = additionalPropertiesSchema(schema, item);
            setRequired(schema, path);
            return;
        }
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
        {
            setRequired(schema, path);
        }
        else
        {
            JSONArray requiredArray = getArray(schema, "required");
            if (!requiredArray.toList().contains(item))
                requiredArray.put(item);
        }
    }

    private static JSONObject oneOfSchema(JSONObject schema, String item)
    {
        final boolean isArray = item.endsWith("[]");
        if (isArray)
            item = item.substring(0, item.length() - 2);
        JSONArray oneOf = getArray(schema, "oneOf");
        int index = Integer.parseInt(item.substring(1));
        schema = oneOf.optJSONObject(index);
        if (schema == null)
        {
            schema = new JSONObject();
            oneOf.put(index, schema);
        }
        if (isArray)
            schema = getObject(schema, "items");
        return schema;
    }

    private static JSONObject additionalPropertiesSchema(JSONObject schema, String item)
    {
        schema = getObject(schema, "additionalProperties");
        if (item.endsWith("[]"))
            schema = getObject(schema, "items");
        return schema;
    }

    /**
     * @return The JSON representation of the Apidoc; a single-line result will not have a trailing
     * newline, while a multi-line will have a trailing newline.
     */
    public static String toString(
        Apidoc apidoc,
        JSONObject root,
        int requiredGroupNameLenLimit,
        boolean generateOrderByParameters,
        boolean jsonrpc) throws Exception
    {
        if (apidoc.groups.isEmpty())
            return "";
        final JSONArray tags = getArray(root, "tags");
        final JSONObject refParameters = getObject(getObject(root, "components"), "parameters");
        final JSONObject componentsSchemas = getObject(getObject(root, "components"), "schemas");
        final HashSet<String> usedTags = new HashSet<String>();
        for (final Apidoc.Group group: apidoc.groups)
        {
            if (!fillPaths(
                getObject(root, "paths"),
                group,
                refParameters,
                componentsSchemas,
                generateOrderByParameters,
                jsonrpc))
            {
                continue;
            }

            if (group.groupName.isEmpty())
                continue;

            if (requiredGroupNameLenLimit > 0 && group.groupName.length() > requiredGroupNameLenLimit)
                throw new Exception("Tag \"" + group.groupName + "\" is too long.");

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
                tag.put("description", Utils.cleanUpDescription(group.groupDescription));
                tags.put(tag);
            }
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
        final String result = root.toString(2);
        if (result.contains("\n") && !result.endsWith("\n"))
            return result + "\n";
        return result;
    }

    private static boolean fillPaths(
        JSONObject paths,
        Apidoc.Group group,
        JSONObject refParameters,
        JSONObject componentsSchemas,
        boolean generateOrderByParameters,
        boolean jsonrpc) throws Exception
    {
        boolean filled = false;
        for (final Apidoc.Function function: group.functions)
        {
            final String pathString = group.urlPrefix + "/" + function.name;
            final JSONObject path = getObject(paths, pathString);
            final JSONObject method = fillPath(path, function, refParameters, componentsSchemas,
                generateOrderByParameters);
            if (jsonrpc)
                addJsonRpcMethods(function, pathString, method);
            if (!group.groupName.isEmpty())
            {
                final JSONArray tags = getArray(method, "tags");
                tags.put(group.groupName);
            }
            filled = true;
        }
        return filled;
    }

    private static void addJsonRpcMethods(Apidoc.Function function, String path, JSONObject method)
    {
        if (function.jsonrpc.unused)
            return;

        String jsonRpcPath = function.pathForJsonRpc(path);
        JSONObject analog = new JSONObject();
        analog.put(function.addJsonRpcSuffix(jsonRpcPath), "Same result.");
        if (function.jsonrpc.subscribeMethod == Apidoc.JsonRpcExt.SubscribeMethod.no)
        {
            method.put("x-jsonrpc-methods", analog);
            return;
        }

        assert function.method.equals("GET");
        JSONObject subscribe = new JSONObject();
        subscribe.put(
            jsonRpcPath + "." +
                (function.jsonrpc.subscribeMethod == Apidoc.JsonRpcExt.SubscribeMethod.list
                    ? "subscribe"
                    : "subscribeOne"),
            function.jsonrpc.subscribeDescription.trim().isEmpty()
                ? "Same result and `update` & `delete` notifications over time."
                : function.jsonrpc.subscribeDescription.trim());
        JSONObject unsubscribe = new JSONObject();
        unsubscribe.put(jsonRpcPath + ".unsubscribe", "Stop over time notifications.");
        JSONArray list = new JSONArray();
        list.put(analog);
        list.put(subscribe);
        list.put(unsubscribe);
        method.put("x-jsonrpc-methods", list);
    }

    private static void processFunctionInputParams(
        Apidoc.Function function,
        JSONObject method,
        JSONObject refParameters,
        JSONObject componentsSchemas) throws Exception
    {
        for (final Apidoc.Param param: function.input.params)
        {
            final boolean inPath = function.name.indexOf("{" + param.name + "}") >= 0;
            if (inPath)
            {
                fillQueryOrPathParameter(method, param, inPath);
                continue;
            }

            if (param.isRef)
            {
                JSONObject parameter;
                for (final String ref: param.name.split(","))
                {
                    if (!refParameters.has(ref))
                        throw new Exception("Ref parameter '" + ref + "' is missing");
                    parameter = new JSONObject();
                    parameter.put("$ref", "#/components/parameters/" + ref);
                    getArray(method, "parameters").put(parameter);
                }
                continue;
            }

            if (param.immutable)
            {
                param.optional = true;
                if (function.method.equals("GET") || function.method.equals("PATCH"))
                    param.readonly = true;
            }
            if (function.areInBodyParameters())
            {
                final JSONObject requestBody = getObject(method, "requestBody");
                if (!param.optional)
                    requestBody.put("required", true);
                JSONObject schema = getObject(getObject(getObject(
                    requestBody, "content"), "application/json"), "schema");
                if (function.input.type.fixed == Apidoc.Type.ARRAY)
                {
                    schema = getObject(schema, "items");
                }
                else if (function.arrayParams)
                {
                    schema.put("type", "array");
                    schema = getObject(schema, "items");
                }

                if (param.recursiveName == null)
                    addStructParam(schema, param, /*fillDefaultExample*/ true);

                continue;
            }

            fillQueryOrPathParameter(method, param, inPath);
        }
        for (final Apidoc.Param param: function.input.params)
        {
            final boolean inPath = function.name.indexOf("{" + param.name + "}") >= 0;
            if (inPath)
                continue;
            if (function.areInBodyParameters() && !param.isRef && param.recursiveName != null)
            {
                final JSONObject requestBody = getObject(method, "requestBody");
                if (!param.optional)
                    requestBody.put("required", true);
                JSONObject schema = getObject(getObject(getObject(
                    requestBody, "content"), "application/json"), "schema");
                if (function.input.type.fixed == Apidoc.Type.ARRAY)
                {
                    schema = getObject(schema, "items");
                }
                else if (function.arrayParams)
                {
                    schema.put("type", "array");
                    schema = getObject(schema, "items");
                }
                addReferenceParam(schema, param, componentsSchemas);
            }
        }

        JSONArray parameters = method.optJSONArray("parameters");
        if (parameters == null)
            return;

        for (int i = 0; i < parameters.length(); ++i)
        {
            JSONObject p = parameters.getJSONObject(i);
            JSONObject c = p.optJSONObject("content");
            if (c != null)
            {
                String description = p.optString("description");
                if (!description.isEmpty())
                    description += "</br>\n";
                p.put("description", description + fieldsDescription(
                    getObject(getObject(c, "application/json"), "schema"), "", ""));
            }
        }
    }

    private static boolean isSimpleType(String name)
    {
        return name.isEmpty()
            || name.startsWith("boolean")
            || name.startsWith("integer")
            || name.startsWith("number")
            || name.equals("string")
            || name.startsWith("string ")
            || name.startsWith("string($uuid)")
            || name.startsWith("one of ");
    }

    private static String oneOfTypeName(JSONArray oneOf)
    {
        String result = "one of [";
        String firstType = typeName(oneOf.getJSONObject(0));
        if (!isSimpleType(firstType))
            return "one of";

        result += firstType;
        for (int i = 1; i < oneOf.length(); ++i)
        {
            String name = typeName(oneOf.getJSONObject(i));
            if (!isSimpleType(name))
                return "one of";

            result += ", " + name;
        }
        return result + "]";
    }

    private static String mapTypeName(JSONObject additionalProperties)
    {
        final String name = typeName(additionalProperties);
        return isSimpleType(name) ? name + " map" : "map";
    }

    private static String arrayTypeName(JSONObject items)
    {
        final String name = typeName(items);
        return isSimpleType(name) ? name + " array" : "array";
    }

    private static String typeName(JSONObject schema)
    {
        final JSONObject additionalProperties = schema.optJSONObject("additionalProperties");
        if (additionalProperties != null)
            return mapTypeName(additionalProperties);

        final JSONArray oneOf = schema.optJSONArray("oneOf");
        if (oneOf != null)
            return oneOfTypeName(oneOf);

        String type = schema.optString("type");
        if (type == null)
            return "";

        if (type.equals("array"))
            return arrayTypeName(getObject(schema, "items"));

        if (type.equals("string"))
        {
            final String format = schema.optString("format");
            if (format.equals("uuid"))
                type = "string($uuid)";
            final JSONArray enum_ = schema.optJSONArray("enum");
            if (enum_ != null)
                type = "string($enum)";
        }
        return type;
    }

    private static String fieldsDescription(JSONObject schema, String indent, String name)
    {
        final String kIndent = "&nbsp;&nbsp;&nbsp;&nbsp;";
        final String kLineBreak = "</br>\n";
        String result = indent;
        if (!name.isEmpty())
            result += "<b>" + name + "</b>";
        final String typeName = typeName(schema);
        if (!typeName.isEmpty())
            result += (name.isEmpty() ? "`" : " `") + typeName + "`";
        result += kLineBreak;
        String description = schema.optString("description");
        if (!description.isEmpty())
        {
            if (description.startsWith("<p>"))
                description = description.substring(3, description.length());
            description = description.replace("\n", kLineBreak + indent + kIndent);
            description = description.replace("<p>", kLineBreak + indent + kIndent);
            description = description.replace("</p>", kLineBreak + indent + kIndent);
            description = description.replace(
                kLineBreak + indent + kIndent + kLineBreak, kLineBreak);
            result += indent + kIndent + description + kLineBreak;
        }
        if (isSimpleType(typeName))
            return result;

        indent += kIndent;

        final JSONObject additionalProperties = schema.optJSONObject("additionalProperties");
        if (additionalProperties != null)
        {
            result += fieldsDescription(additionalProperties, indent, "");
            return result;
        }

        if (typeName.equals("object"))
        {
            JSONObject properties = schema.optJSONObject("properties");
            if (properties == null)
                return result;

            for (final String k: properties.keySet())
                result += fieldsDescription(getObject(properties, k), indent, k);
            return result;
        }

        if (typeName.equals("array"))
        {
            result += fieldsDescription(getObject(schema, "items"), indent, "");
            return result;
        }

        final JSONArray oneOf = schema.optJSONArray("oneOf");
        if (oneOf != null)
        {
            for (int i = 0; i < oneOf.length(); ++i)
                result += fieldsDescription(oneOf.getJSONObject(i), indent, "");
            return result;
        }

        if (typeName.equals("string($enum)") && !description.contains("Possible values are"))
        {
            final JSONArray enum_ = getArray(schema, "enum");
            if (enum_.length() > 0)
            {
                result += indent + "Possible values are:" + kLineBreak;
                indent += kIndent;
                for (int i = 0; i < enum_.length(); ++i)
                    result += indent + "`" + enum_.getString(i) + "`" + kLineBreak;
            }
        }

        return result;
    }

    private static JSONObject fillPath(
        JSONObject path,
        Apidoc.Function function,
        JSONObject refParameters,
        JSONObject componentsSchemas,
        boolean generateOrderByParameters) throws Exception
    {
        final JSONObject method = getObject(path, function.knownMethod());
        if (!function.caption.isEmpty())
            method.put("summary", function.caption);

        String description = new String();

        if (function.deprecated)
        {
            method.put("deprecated", true);
            String cleanedDescription = Utils.cleanUpDescription(function.deprecatedDescription);
            if (!cleanedDescription.isEmpty())
                description += String.format("<p><b>%s</b></p>", cleanedDescription);
        }

        if (function.proprietary)
            description += "<p><b>Proprietary.</b></p>";

        String cleanedDescription = Utils.cleanUpDescription(function.description);
        if (!cleanedDescription.isEmpty())
            description += cleanedDescription;

        if (!description.isEmpty())
            method.put("description", description);
        if (function.permissions != null && !function.permissions.isEmpty())
            method.put("x-permissions", function.permissions);
        if (function.input.type.fixed != Apidoc.Type.UNKNOWN && function.areInBodyParameters())
        {
            final JSONObject requestBody = getObject(method, "requestBody");
            if (!function.input.optional)
                requestBody.put("required", true);
            JSONObject schema = getObject(getObject(getObject(
                requestBody, "content"),
                function.input.type.fixed == Apidoc.Type.BINARY
                    ? "application/octet-stream"
                    : "application/json"),
                "schema");
            fillSchemaType(schema, function.input.type, /*fillDefaultExample*/ true);
            if (!function.input.example.isEmpty())
                schema.put("example", function.input.type.parse(function.input.example));
        }
        processFunctionInputParams(function, method, refParameters, componentsSchemas);
        for (final Apidoc.Param param: function.input.params)
        {
            if (param.name.equals("_orderBy"))
            {
                generateOrderByParameters = false;
                break;
            }
        }
        fillResult(method, function, componentsSchemas, generateOrderByParameters);
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
        if (param.type.fixed == Apidoc.Type.ARRAY
            || param.type.fixed == Apidoc.Type.STRING_ARRAY
            || param.type.fixed == Apidoc.Type.UUID_ARRAY
            || param.type.fixed == Apidoc.Type.OBJECT)
        {
            return orderBy;
        }
        final int lastCharOfArrayName = param.name.lastIndexOf("[]");
        if (orderBy != null || lastCharOfArrayName != -1)
        {
            if (orderBy == null)
                orderBy = orderByTemplate();
            final JSONObject schema = orderBy.getJSONObject("schema");
            final JSONArray enum_ = getArray(schema.getJSONObject("items"), "enum");
            enum_.put(param.name);
        }
        return orderBy;
    }

    private static void fillResult(
        JSONObject path,
        Apidoc.Function function,
        JSONObject componentsSchemas,
        boolean generateOrderByParameters) throws Exception
    {
        final JSONObject default_ = getObject(getObject(path, "responses"), "default");
        final Apidoc.Result result = function.result;
        default_.put("description", Utils.cleanUpDescription(result.caption));
        if (result.type.fixed == Apidoc.Type.UNKNOWN)
            return;
        JSONObject schema = getObject(getObject(getObject(
            default_, "content"), "application/json"), "schema");
        fillSchemaType(schema, result.type, /*fillDefaultExample*/ false);
        if (!result.example.isEmpty())
            schema.put("example", result.type.parse(result.example));
        if (result.type.fixed == Apidoc.Type.ARRAY || result.type.fixed == Apidoc.Type.OBJECT)
        {
            JSONObject orderBy = null;
            if (result.type.fixed == Apidoc.Type.ARRAY)
            {
                schema = schema.getJSONObject("items");
                if (generateOrderByParameters)
                    orderBy = orderByTemplate();
            }
            for (final Apidoc.Param param: result.params)
            {
                if (param.immutable)
                {
                    param.optional = true;
                    param.readonly = true;
                }
                if (param.recursiveName == null)
                    addStructParam(schema, param, /*fillDefaultExample*/ false);
                if (generateOrderByParameters)
                    orderBy = fillOrderBy(orderBy, param);
            }
            if (orderBy != null)
                getArray(path, "parameters").put(orderBy);
            for (final Apidoc.Param param: result.params)
            {
                if (param.recursiveName != null)
                    addReferenceParam(schema, param, componentsSchemas);
            }
        }
    }

    private static void fillSchemaType(
        JSONObject schema, Apidoc.Type type, boolean fillDefaultExample)
    {
        switch (type)
        {
            case UNKNOWN:
            case ANY:
                break;
            case OBJECT_JSON:
            case ARRAY_JSON:
            case TEXT:
            case STRING:
            case ENUM:
            case FLAGS:
                schema.put("type", "string");
                if (fillDefaultExample && type == Apidoc.Type.STRING)
                    schema.put("example", "");
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
                schema.put("example", "89abcdef-0123-4567-89ab-cdef01234567");
                break;
            case OBJECT:
                schema.put("type", "object");
                break;
            case ARRAY:
                schema.put("type", "array");
                getObject(schema, "items");
                break;
            case STRING_ARRAY:
                schema.put("type", "array");
                schema = getObject(schema, "items");
                schema.put("type", "string");
                if (fillDefaultExample)
                    schema.put("example", "");
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

    private static void fillSchemaType(
        JSONObject schema, TypeInfo typeInfo, boolean fillDefaultExample)
    {
        if (typeInfo.variantValueTypes != null)
        {
            if (typeInfo.fixed == Apidoc.Type.ARRAY)
            {
                schema.put("type", "array");
                schema = getObject(schema, "items");
            }
            if (typeInfo.canBeNull)
                schema.put("nullable", true);
            final JSONArray oneOf = getArray(schema, "oneOf");
            for (int i = 0; i < typeInfo.variantValueTypes.size(); ++i)
            {
                TypeInfo type = typeInfo.variantValueTypes.get(i);
                assert type.fixed != Apidoc.Type.UNKNOWN;
                JSONObject internalSchema = new JSONObject();
                fillSchemaType(internalSchema, type, fillDefaultExample);
                oneOf.put(i, internalSchema);
            }
            return;
        }
        if (typeInfo.mapValueType != null)
        {
            assert typeInfo.mapValueType.fixed != Apidoc.Type.UNKNOWN;
            if (typeInfo.fixed == Apidoc.Type.ARRAY)
            {
                schema.put("type", "array");
                schema = getObject(schema, "items");
            }
            fillSchemaType(
                getObject(schema, "additionalProperties"),
                typeInfo.mapValueType,
                fillDefaultExample);
            return;
        }
        if (typeInfo.isChrono() && typeInfo.fixed == Apidoc.Type.ARRAY)
        {
            schema.put("type", "array");
            getObject(schema, "items").put("type", "integer");
            return;
        }
        fillSchemaType(schema, typeInfo.fixed, fillDefaultExample);
    }

    private static void fillSchemaType(
        JSONObject schema, Apidoc.Param param, boolean fillDefaultExample)
    {
        fillSchemaType(schema, param.type, fillDefaultExample);
        putExample(param, schema);
        if (param.type.fixed == Apidoc.Type.ENUM || param.type.fixed == Apidoc.Type.FLAGS)
        {
            if (param.values.isEmpty())
                return;
            final JSONArray enum_ = getArray(schema, "enum");
            for (final Apidoc.Value value: param.values)
            {
                if (!value.unused)
                    enum_.put(value.name);
            }
        }
    }

    private static String description(
        boolean proprietary, String description, boolean deprecated, String deprecatedDescription)
        throws Exception
    {
        String result = proprietary ? "<p><b>Proprietary.</b></p>" : "";
        if (deprecated)
        {
            String cleanedDescription = Utils.cleanUpDescription(deprecatedDescription);
            result += String.format("<p><b>Deprecated.</b>%s</p>",
                !cleanedDescription.isEmpty() ? " " + cleanedDescription : "");
        }
        result += Utils.cleanUpDescription(description);
        return result;
    }

    private static String description(Apidoc.Param param) throws Exception
    {
        String result = description(
            param.proprietary, param.description, param.deprecated, param.deprecatedDescription);
        if (param.values.isEmpty())
            return result;
        if (param.type.fixed == Apidoc.Type.BOOLEAN
            || param.type.fixed == Apidoc.Type.ENUM
            || param.type.fixed == Apidoc.Type.FLAGS)
        {
            boolean hasDescription = false;
            for (final Apidoc.Value value: param.values)
            {
                if (value.unused)
                    continue;

                if (value.deprecated
                    || value.proprietary
                    || !description(
                        value.proprietary,
                        value.description,
                        value.deprecated,
                        value.deprecatedDescription).isEmpty())
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
        if (param.type.fixed == Apidoc.Type.FLAGS)
            result += "Possible values are one of or the combination by `|` of the following:";
        else
            result += "Possible values are:";
        for (final Apidoc.Value value: param.values)
        {
            if (value.unused)
                continue;

            result += "\n- `" + value.nameForDescription(param.type.fixed) + '`';
            String description = description(
                value.proprietary,
                value.description,
                value.deprecated,
                value.deprecatedDescription);
            if (!description.isEmpty())
            {
                if (!value.deprecated && !value.proprietary)
                    result += ' ';
                result += description;
            }
        }
        return result;
    }

    private static void putDescription(Apidoc.Param param, JSONObject object) throws Exception
    {
        String result = description(param);
        if (!result.isEmpty())
            object.put("description", result);
    }

    private static void addStructParam(
        JSONObject schema, Apidoc.Param param, boolean fillDefaultExample) throws Exception
    {
        final JSONObject parameter = getParamByPath(schema, param.name);
        putDescription(param, parameter);
        if (param.deprecated)
            parameter.put("deprecated", true);
        if (param.readonly)
            parameter.put("readOnly", true);
        else if (!param.optional)
            setRequired(schema, param.name);
        fillSchemaType(parameter, param, fillDefaultExample);
    }

    private static void addReferenceParam(
        JSONObject schema, Apidoc.Param param, JSONObject componentsSchemas)
    {
        String recursiveName = param.recursiveName;
        if (recursiveName.endsWith("."))
            recursiveName = recursiveName.substring(0, recursiveName.length() - 1);
        if (recursiveName.endsWith("[]"))
            recursiveName = recursiveName.substring(0, recursiveName.length() - 2);
        final JSONObject recursive =
            recursiveName.isEmpty() ? schema : getParamByPath(schema, recursiveName);
        final JSONObject parameter = getParamByPath(schema, param.name);
        if (param.readonly)
            parameter.put("readOnly", true);
        if (!param.optional)
            setRequired(schema, param.name);
        if (param.type.fixed == Apidoc.Type.ARRAY)
        {
            parameter.put("type", "array");
            getObject(parameter, "items").put("$ref", "#/components/schemas/" + param.type.name);
        }
        else
        {
            parameter.put("$ref", "#/components/schemas/" + param.type.name);
        }
        componentsSchemas.put(
            param.type.name, recursive.has("items") ? recursive.get("items") : recursive);
    }

    private static void fillQueryOrPathParameter(
        JSONObject method, Apidoc.Param param, boolean inPath) throws Exception
    {
        JSONArray parameters = getArray(method, "parameters");
        if (param.name.contains("."))
        {
            String[] items = param.name.split("\\.");
            for (int i = 0; i < parameters.length(); ++i)
            {
                JSONObject parameter = parameters.getJSONObject(i);
                String field = items[0];
                boolean isArray = field.endsWith("[]");
                if (isArray)
                    field = field.substring(0, field.length() - 2);
                if (parameter.getString("name").equals(field))
                {
                    parameter.remove("schema");
                    JSONObject schema = getObject(getObject(getObject(
                        parameter, "content"), "application/json"), "schema");
                    if (isArray || param.type.fixed == Apidoc.Type.ARRAY)
                    {
                        schema.put("type", "array");
                        schema = getObject(schema, "items");
                    }
                    boolean readonly = param.readonly;
                    param.readonly = false;
                    String name = param.name;
                    param.name = items[1];
                    for (int j = 2; j < items.length; ++j)
                        param.name += '.' + items[j];
                    addStructParam(schema, param, /*fillDefaultExample*/ true);
                    param.name = name;
                    param.readonly = readonly;
                    break;
                }
            }
        }
        else
        {
            final JSONObject parameter = new JSONObject();
            parameter.put("name", param.name);
            putDescription(param, parameter);
            if (param.deprecated)
                parameter.put("deprecated", true);
            if (!param.readonly && !param.optional)
                parameter.put("required", true);
            if (inPath)
            {
                parameter.put("in", "path");
                parameter.remove("readOnly");
                parameter.put("required", true);
            }
            else
            {
                parameter.put("in", "query");
            }
            JSONObject schemaContainer = (param.type.fixed == Apidoc.Type.OBJECT && !param.type.isChrono())
                ? getObject(getObject(parameter, "content"), "application/json")
                : parameter;
            fillSchemaType(
                getObject(schemaContainer, "schema"), param, /*fillDefaultExample*/ true);
            parameters.put(parameter);
        }
    }

    private static void putExample(Apidoc.Param param, JSONObject result)
    {
        if (!param.example.isEmpty())
        {
            result.put("example", param.type.parse(param.example));
            return;
        }

        if (!param.needExample())
            return;

        for (final Apidoc.Value value: param.values)
        {
            if (value.deprecated || value.proprietary || value.unused)
                continue;

            result.put("example", param.type.parse(value.name));
            return;
        }
    }
}
