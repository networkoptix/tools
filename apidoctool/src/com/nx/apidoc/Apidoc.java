// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.nx.utils.Serializable;
import com.nx.utils.Utils;

import static com.nx.apidoc.ApidocComment.*;

/**
 * Object representation of apidoc elements. Empty Strings and ArrayLists
 * are used to represent missing values (never null).
 */
public final class Apidoc extends Serializable
{
    public enum Type
    {
        UNKNOWN,
        STRING,
        BOOLEAN,
        INTEGER,
        ENUM,
        FLOAT,
        UUID,
        OBJECT, //< Inner object.
        ARRAY, //< List of objects.
        OPTION, //< Parameter without value.
        FLAGS, //< Combination of flags separated with "|".
        STRING_ARRAY, //< List of strings.
        UUID_ARRAY, //< List of uuids.
        OBJECT_JSON, //< String with JSON object inside.
        ARRAY_JSON, //< String with JSON array inside.
        BASE64, //< Base64-encoded string.
        TEXT, //< Raw text in result.
        BINARY, //< Raw binary data in result.
        ANY; //< Arbitrary type.

        public static Type fromString(String value)
        {
            if (value.isEmpty())
                return values()[0];

            return values()[stringValues.indexOf(value)];
        }

        public String toString()
        {
            return stringValues.get(ordinal());
        }

        public static final List<String> stringValues = new ArrayList<String>();

        static
        {
            for (Type value: values())
                stringValues.add(Utils.toCamelCase(value.name()));
        }

        public boolean mustBeQuotedInInput()
        {
            return this == STRING;
        }

        public boolean mustBeUnquotedInInput()
        {
            return this == BOOLEAN || this == ENUM || this == FLAGS || this == INTEGER
                || this == OPTION || this == UUID;
        }

        public boolean mustBeQuotedInOutput()
        {
            return this == ENUM || this == FLAGS || this == STRING || this == UUID;
        }

        public boolean mustBeUnquotedInOutput()
        {
            return this == BOOLEAN || this == INTEGER || this == OPTION;
        }
    }

    public static final class Value extends Serializable implements Cloneable
    {
        public String name;
        public String description; ///< optional
        public boolean proprietary; ///< optional
        public boolean deprecated; ///< optional
        public boolean unused; ///< optional
        public String deprecatedDescription = "";
        public boolean areQuotesRemovedFromName = false;

        public Value clone()
        {
            try
            {
                return (Value) super.clone();
            }
            catch (CloneNotSupportedException e)
            {
                throw new IllegalStateException(e);
            }
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            setName(p.readString("name", Presence.REQUIRED));
            unused = p.readBoolean("unused", BooleanDefault.FALSE);
            proprietary = p.readBoolean("proprietary", BooleanDefault.FALSE);
            deprecated = p.readBoolean("deprecated", BooleanDefault.FALSE);
            description = p.readInnerXml("description", Presence.OPTIONAL);
            stripDeprecatedDescriptionFromDescription();
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeBoolean("unused", unused, BooleanDefault.FALSE);
            g.writeBoolean("proprietary", proprietary, BooleanDefault.FALSE);
            g.writeBoolean("deprecated", deprecated, BooleanDefault.FALSE);

            g.writeString(
                "name",
                areQuotesRemovedFromName ? ('"' + name + '"') : name,
                Emptiness.PROHIBIT);

            final String deprecatedString = getDeprecatedString();
            final String descriptionString = (description == null) ? "" : description;
            g.writeInnerXml("description", deprecatedString + descriptionString, Emptiness.ALLOW);
        }

        public void setName(String name)
        {
            name = name.trim();
            // TODO: Support a name in quotes separated by space.
            if ((name.length() >= 2) && name.startsWith("\"") && name.endsWith("\""))
            {
                name = name.substring(/*beginIndex*/ 1, /*endIndex*/ name.length() - 1);
                areQuotesRemovedFromName = true;
            }
            this.name = name;
        }

        public String nameForDescription(Apidoc.Type type)
        {
            if (type.mustBeUnquotedInOutput())
                return name;
            if (areQuotesRemovedFromName || type.mustBeQuotedInOutput())
                return '"' + name + '"';
            return name;
        }

        public String getDeprecatedString()
        {
            return deprecated
                ? String.format(
                    "<p><b>Deprecated.</b>%s</p>",
                    !deprecatedDescription.isEmpty()
                        ? " " + deprecatedDescription
                        : "")
                : "";
        }

        private void stripDeprecatedDescriptionFromDescription()
        {
            Pattern pattern = Pattern.compile("<p>[ \\n]*<b>Deprecated\\.</b>([ \\n]|.)*</p>");
            Matcher matcher = pattern.matcher(description);
            if (matcher.find())
            {
                final String deprecatedString = matcher.group(0);
                description = description.replace(deprecatedString, "").trim();
                pattern = Pattern.compile("</b>.+</p>");
                matcher = pattern.matcher(deprecatedString);
                deprecatedDescription = matcher.find()
                    ? matcher.group(0).replaceAll("(</b>)|(</p>)", "").trim()
                    : "";
            }
        }
    }

    public static final class Param extends Serializable
    {

        public boolean isGeneratedFromStruct = false;
        public boolean unused = false; ///< Internal field, omit param from apidoc.
        public boolean hasDefaultDescription = false; ///< Internal field
        public boolean isRef = false; ///< Internal field
        public String recursiveName; ///< Internal field

        public boolean proprietary = false; ///< attribute; optional(default=false)
        public boolean deprecated = false; ///< attribute; optional(default=false)
        public boolean readonly = false; ///< attribute; optional(default=false)
        public boolean immutable = false; ///< attribute; optional(default=false)
        public String name;
        public TypeInfo type;
        public String description; ///< optional
        public String deprecatedDescription = ""; ///< optional
        public boolean optional = false; ///< attribute; optional(default=false)
        public List<Value> values; ///< optional
        public String example = ""; ///< optional

        public Param()
        {
            type = new TypeInfo();
            values = new ArrayList<Value>();
        }

        public void fillMissingFieldsFrom(Param origin) throws Error
        {
            if (!isGeneratedFromStruct)
                isGeneratedFromStruct = origin.isGeneratedFromStruct;
            type.fillMissingType(origin.type);
            if (!unused)
                unused = origin.unused;
            if (!hasDefaultDescription)
                hasDefaultDescription = origin.hasDefaultDescription;
            if (!proprietary)
                proprietary = origin.proprietary;
            if (!deprecated)
            {
                deprecated = origin.deprecated;
                if (deprecatedDescription.isEmpty())
                    deprecatedDescription = origin.deprecatedDescription;
            }
            if (!readonly)
                readonly = origin.readonly;
            if (!immutable)
                immutable = origin.immutable;
            if (name == null || name.isEmpty())
                name = origin.name;
            if (description == null || description.isEmpty())
                description = origin.description;
            if (!optional)
                optional = origin.optional;
            if (recursiveName == null)
                recursiveName = origin.recursiveName;
            if (example.isEmpty())
                example = origin.example;

            if (origin.values == null || origin.values.isEmpty())
                return;

            if ((this.values == null || this.values.isEmpty()) && !Apidoc.enableEnumValueMerge)
            {
                List<Apidoc.Value> tempValues = new ArrayList<Apidoc.Value>();
                for (final Apidoc.Value originValue: origin.values)
                    tempValues.add(originValue.clone());

                this.values = tempValues;
                return;
            }

            if (Apidoc.enableEnumValueMerge)
                mergeEnumValues(origin.values);
        }

        public void normalizeProperties()
        {
            squashValueProperties();
        }

        public String getDeprecatedString()
        {
            return deprecated
                ? String.format(
                    "<p><b>Deprecated.</b>%s</p>",
                    !deprecatedDescription.isEmpty()
                        ? " " + deprecatedDescription
                        : "")
                : "";
        }

        public boolean needExample()
        {
            if (unused || isRef || proprietary || deprecated || readonly || optional)
                return false;

            if (type.mapValueType != null || type.variantValueTypes != null)
                return false;

            if (type.fixed == Type.UNKNOWN
                || type.fixed == Type.BOOLEAN
                || type.fixed == Type.ARRAY
                || type.fixed == Type.OBJECT)
            {
                return false;
            }

            return true;
        }

        public boolean isUnusedOrderBy()
        {
            return unused && PARAM_ORDER_BY.equals(name);
        }

        private void mergeEnumValues(List<Apidoc.Value> originValues) throws Error
        {
            for (final Apidoc.Value value: this.values)
            {
                if (originValues.stream().filter(val -> val.name.equals(value.name)).count() == 0)
                    throw new Error("Value " + "\"" + value.name + "\" must be included in \"" + this.name + "\" enum");
            }

            List<Apidoc.Value> tempValues = new ArrayList<Apidoc.Value>();
            for (final Apidoc.Value originValue: originValues)
            {
                Apidoc.Value tempValue = originValue.clone();
                final Object[] filteredByName = this.values.stream().filter(
                    val -> val.name.equals(tempValue.name)).toArray();
                if (filteredByName.length > 0)
                {
                    Apidoc.Value value = (Apidoc.Value) filteredByName[0];
                    mergeEnumValue(tempValue, value);
                }
                tempValues.add(tempValue);
            }
            this.values = tempValues;
        }

        private void mergeEnumValue(Apidoc.Value originValue, Apidoc.Value value)
        {
            if (!originValue.unused || this.unused)
                originValue.unused = !this.unused && value.unused;

            if (!originValue.proprietary || this.proprietary)
                originValue.proprietary = !this.proprietary && value.proprietary;

            if (!originValue.deprecated || this.deprecated)
                originValue.deprecated = !this.deprecated && value.deprecated;

            if (originValue.deprecated
                && (originValue.deprecatedDescription == null
                || originValue.deprecatedDescription.isEmpty()))
            {
                originValue.deprecatedDescription = value.deprecatedDescription;
            }

            if (value.description != null && !value.description.isEmpty())
                originValue.description = value.description;
        }

        private void squashValueProperties()
        {
            if (this.values.isEmpty())
                return;

            boolean areAllValuesProprietary = true;
            boolean areAllValuesDeprecated = true;
            for (final Apidoc.Value value: this.values)
            {
                if (value.unused)
                    continue;

                areAllValuesProprietary &= value.proprietary;
                areAllValuesDeprecated &= value.deprecated;

                if (!areAllValuesProprietary && !areAllValuesDeprecated)
                    break;
            }

            if (areAllValuesProprietary)
                this.proprietary = true;
            if (areAllValuesDeprecated)
                this.deprecated = true;

            if (this.proprietary)
                this.values.stream().forEach(val -> val.proprietary = false);
            if (this.deprecated)
                this.values.stream().forEach(val -> val.deprecated = false);
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            proprietary = p.readBoolean("proprietary", BooleanDefault.FALSE);
            name = p.readString("name", Presence.REQUIRED);
            type.fixed = p.readEnum("type", Type.stringValues, Type.class, Presence.OPTIONAL);
            description = p.readInnerXml("description", Presence.OPTIONAL);
            optional = p.readBoolean("optional", BooleanDefault.FALSE);
            p.readObjectList("values", values, Value.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            if (proprietary)
                g.writeBoolean("proprietary", true, BooleanDefault.NONE);

            g.writeString("name", name, Emptiness.PROHIBIT);
            g.writeEnum("type", type.fixed, Type.class, EnumDefault.OMIT);
            final String deprecatedString = getDeprecatedString();
            g.writeInnerXml(
                "description",
                !deprecatedString.isEmpty()
                    ? deprecatedString + description
                    : description,
                Emptiness.ALLOW);
            g.writeBoolean("optional", optional, BooleanDefault.NONE);
            g.writeObjectList("values", values, Emptiness.OMIT);
        }
    }

    public static class InOutData extends Serializable
    {
        public TypeInfo type = new TypeInfo();
        public List<Param> unusedParams = new ArrayList<Param>(); ///< Internal field.
        public List<Param> params = new ArrayList<Param>(); ///< optional
        public boolean optional = false; ///< attribute; optional(false)
        public String example = ""; ///< tag; optional

        protected void readFromParser(Parser p) throws Parser.Error
        {
            type.fixed = p.readEnum("type", Type.stringValues, Type.class, Presence.OPTIONAL);
            p.readObjectList("params", params, Param.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeEnum("type", type.fixed, Type.class, EnumDefault.OMIT);
            g.writeObjectList("params", params, Emptiness.OMIT);
        }
    }

    public static final class Result extends InOutData
    {
        public String caption = ""; ///< optional

        protected void readFromParser(Parser p) throws Parser.Error
        {
            caption = p.readInnerXml("caption", Presence.OPTIONAL);
            super.readFromParser(p);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeInnerXml("caption", caption, Emptiness.OMIT);
            super.writeToGenerator(g);
        }
    }

    public static final class JsonRpcExt
    {
        boolean unused = false;
        String resultMethod = "";
        String resultDescription = "";
        String subscribeDescription = null;

        void parse(ApidocTagParser.Item item, int indentLevel) throws ApidocCommentParser.Error
        {
            String name = item.getInitialToken();
            if (ATTR_UNUSED.equals(item.getAttribute()))
            {
                if (unused)
                {
                    throw new ApidocCommentParser.Error(item.getErrorPrefix() + TAG_JSONRPC +
                        ATTR_UNUSED + " is specified more than once.");
                }
                if (!"".equals(name))
                {
                    throw new ApidocCommentParser.Error(item.getErrorPrefix() +
                        TAG_JSONRPC + ATTR_UNUSED + " must not specify anything.");
                }
                if (!resultMethod.isEmpty() || subscribeDescription != null)
                {
                    throw new ApidocCommentParser.Error(item.getErrorPrefix() + TAG_JSONRPC +
                        ATTR_UNUSED + " can not be specified in conjunction with any other " +
                        TAG_JSONRPC + ".");
                }
                unused = true;
                return;
            }

            if (unused)
            {
                throw new ApidocCommentParser.Error(item.getErrorPrefix() + "Any other " +
                    TAG_JSONRPC + " usages can not be specified in conjunction with " +
                    TAG_JSONRPC + ATTR_UNUSED + ".");
            }

            if (ATTR_RESULT.equals(item.getAttribute()))
            {
                if (!resultMethod.isEmpty())
                {
                    throw new ApidocCommentParser.Error(item.getErrorPrefix() + TAG_JSONRPC +
                        ATTR_RESULT + " is specified more than once.");
                }
                if (name.equals(PARAM_ONE) || name.equals(PARAM_ALL))
                {
                    resultMethod = name;
                }
                else
                {
                    throw new ApidocCommentParser.Error(item.getErrorPrefix() + "Unknown " +
                        TAG_JSONRPC + ATTR_RESULT + " type `" + name + "`.");
                }

                resultDescription = item.getTextAfterInitialToken(indentLevel).trim();
                return;
            }

            if (!"".equals(item.getAttribute()))
            {
                throw new ApidocCommentParser.Error(item.getErrorPrefix() +
                    "Unsupported attribute `" + item.getAttribute() + "` for " + TAG_JSONRPC + ".");
            }

            if (name.equals(PARAM_SUBSCRIBE))
            {
                if (subscribeDescription != null)
                {
                    throw new ApidocCommentParser.Error(item.getErrorPrefix() + TAG_JSONRPC +
                        " " + PARAM_SUBSCRIBE + " must be specified only once.");
                }
                subscribeDescription = item.getTextAfterInitialToken(indentLevel).trim();
                return;
            }

            throw new ApidocCommentParser.Error(item.getErrorPrefix() + "Unknown " + TAG_JSONRPC +
                " extension name `" + name + "`.");
        }
    }

    public static final class Function extends Serializable
    {
        public boolean arrayParams; ///< optional(false)
        public boolean proprietary; ///< attribute; optional(false)
        public boolean deprecated; ///< attribute; optional(false)
        public String name;
        public String caption = ""; ///< optional
        public List<String> groups = new ArrayList<String>();
        public String description; ///< optional
        public String permissions; ///< optional
        public String method; ///< optional
        public String deprecatedDescription = ""; ///< optional
        public InOutData input = new InOutData(); ///< optional
        public Result result = new Apidoc.Result(); ///< optional
        public JsonRpcExt jsonrpc = new JsonRpcExt(); ///< optional

        public boolean areInBodyParameters()
        {
            return method.equals("POST") || method.equals("PUT") || method.equals("PATCH")
                || /* Used as a stub method. */ method.equals("TRACE");
        }

        public String knownMethod()
        {
            if (method.isEmpty())
                return "options";
            final List<String> knownMethods = Arrays.asList(
                "get", "post", "put", "patch", "delete", "head", "options", "trace");
            final String result = method.toLowerCase();
            return knownMethods.contains(result) ? result : "trace";
        }

        public String jsonRpcMethod(final String originPath)
        {
            assert originPath.length() > 1 && originPath.charAt(0) == '/';
            String path = originPath.substring(1);
            for (Param p: input.params)
            {
                path = path.replace("/{" + p.name + "}", "");
                path = path.replace("/*", "");
            }
            path = path.replace("/", ".");

            if (jsonrpc.resultMethod.isEmpty())
            {
                if (method.equals("GET"))
                {
                    return path + "." + (result.type.fixed == Type.ARRAY
                        || result.type.fixed == Type.STRING_ARRAY
                        || result.type.fixed == Type.UUID_ARRAY
                            ? PARAM_ALL
                            : PARAM_ONE);
                }
                return path + jsonRpcMethods.get(method);
            }

            return path + "." + jsonrpc.resultMethod;
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            proprietary = p.readBoolean("proprietary", BooleanDefault.FALSE);
            arrayParams = p.readBoolean("arrayParams", BooleanDefault.FALSE);
            name = p.readString("name", Presence.REQUIRED);
            caption = p.readString("caption", Presence.OPTIONAL);
            description = p.readInnerXml("description", Presence.OPTIONAL);
            permissions = p.readString("permissions", Presence.OPTIONAL);
            method = p.readString("method", Presence.OPTIONAL);
            p.readObjectList("params", input.params, Param.class, Presence.OPTIONAL);
            result = p.readObject("result", Result.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            if (proprietary)
                g.writeBoolean("proprietary", true, BooleanDefault.NONE);

            g.writeBoolean("arrayParams", arrayParams, BooleanDefault.FALSE);
            g.writeString("name", name, Emptiness.PROHIBIT);
            g.writeString("caption", caption, Emptiness.OMIT);
            g.writeInnerXml("description", getDeprecatedString() + description, Emptiness.ALLOW);
            g.writeString("permissions", permissions, Emptiness.OMIT);
            g.writeString("method", method, Emptiness.ALLOW);
            g.writeObjectList("params", input.params, Emptiness.ALLOW);
            g.writeObject("result", result, Emptiness.ALLOW);
        }

        public String getDeprecatedString()
        {
            return deprecated
                ? String.format(
                "<p><b>Deprecated.</b>%s</p>",
                !deprecatedDescription.isEmpty()
                    ? " " + deprecatedDescription
                    : "")
                : "";
        }

        private static final Map<String, String> jsonRpcMethods = new HashMap<String, String>()
        {
            {
                put("POST", ".create");
                put("PUT", ".set");
                put("PATCH", ".update");
                put("DELETE", ".delete");
            }
        };
    }

    public static final class Group extends Serializable
    {
        public String groupName;
        public String urlPrefix; ///< Used by legacy API only.
        public String groupDescription;
        public List<Function> functions; ///< optional

        public Group()
        {
            functions = new ArrayList<Function>();
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            groupName = p.readString("groupName", Presence.REQUIRED);
            urlPrefix = p.readString("urlPrefix", Presence.OPTIONAL);
            groupDescription = p.readString("groupDescription", Presence.OPTIONAL);
            p.readObjectList("functions", functions, Function.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeString("groupName", groupName, Emptiness.PROHIBIT);
            g.writeString("urlPrefix", urlPrefix, Emptiness.ALLOW);
            g.writeString("groupDescription", groupDescription, Emptiness.ALLOW);
            g.writeObjectList("functions", functions, Emptiness.OMIT);
        }
    }

    //--------------------------------------------------------------------------

    public List<Group> groups;
    public static boolean enableEnumValueMerge = false;

    public Apidoc()
    {
        groups = new ArrayList<Group>();
    }

    protected void readFromParser(Parser p) throws Parser.Error
    {
        p.readObjectList("groups", groups, Group.class, Presence.REQUIRED);
    }

    protected void writeToGenerator(Generator g)
    {
        g.writeObjectList("groups", groups, Emptiness.PROHIBIT);
    }
}
