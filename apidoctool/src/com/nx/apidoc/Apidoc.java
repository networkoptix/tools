package com.nx.apidoc;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import com.nx.util.Serializable;
import com.nx.util.Utils;

/**
 * Object representation of apidoc XML elements. Empty Strings and ArrayLists
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
            proprietary = p.readBooleanAttr("proprietary", BooleanDefault.FALSE);
            deprecated = p.readBooleanAttr("deprecated", BooleanDefault.FALSE);
            description = p.readInnerXml("description", Presence.OPTIONAL);
            stripDeprecatedDescriptionFromDescription();
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeBooleanAttr("proprietary", proprietary, BooleanDefault.FALSE);
            g.writeBooleanAttr("deprecated", deprecated, BooleanDefault.FALSE);

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
        private boolean omitOptionalFieldIfFalse = false; ///< Used for serializing.

        public boolean unused = false; ///< Internal field, omit param from apidoc.
        public boolean hasDefaultDescription = false; ///< Internal field
        public boolean isRef = false; ///< Internal field
        public String recursiveName; ///< Internal field

        public boolean proprietary = false; ///< attribute; optional(default=false)
        public boolean deprecated = false; ///< attribute; optional(default=false)
        public boolean readonly = false; ///< attribute; optional(default=false)
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
            if (!omitOptionalFieldIfFalse)
                omitOptionalFieldIfFalse = origin.omitOptionalFieldIfFalse;
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
                || type.fixed == Type.ENUM
                || type.fixed == Type.FLAGS
                || type.fixed == Type.ARRAY
                || type.fixed == Type.OBJECT)
            {
                return false;
            }

            return true;
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
            proprietary = p.readBooleanAttr("proprietary", BooleanDefault.FALSE);
            name = p.readString("name", Presence.REQUIRED);
            type.fixed = p.readEnum("type", Type.stringValues, Type.class, Presence.OPTIONAL);
            description = p.readInnerXml("description", Presence.OPTIONAL);
            optional = p.readBoolean("optional", BooleanDefault.FALSE);
            p.readObjectList("values", values, Value.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            if (proprietary)
                g.writeBooleanAttr("proprietary", true, BooleanDefault.NONE);

            g.writeString("name", name, Emptiness.PROHIBIT);
            g.writeEnum("type", type.fixed, Type.class, EnumDefault.OMIT);
            final String deprecatedString = getDeprecatedString();
            g.writeInnerXml(
                "description",
                !deprecatedString.isEmpty()
                    ? deprecatedString + description
                    : description,
                Emptiness.ALLOW);
            g.writeBoolean(
                "optional", optional,
                omitOptionalFieldIfFalse ? BooleanDefault.FALSE : BooleanDefault.NONE);
            g.writeObjectList("values", values, Emptiness.OMIT);
        }
    }

    public static class InOutData extends Serializable
    {
        public TypeInfo type;
        public List<Param> unusedParams; ///< Internal field.
        public List<Param> params; ///< optional
        public boolean optional; ///< attribute; optional(false)

        public InOutData()
        {
            type = new TypeInfo();
            params = new ArrayList<Param>();
            unusedParams = new ArrayList<Param>();
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            type.fixed = p.readEnum("type", Type.stringValues, Type.class, Presence.OPTIONAL);
            p.readObjectList("params", params, Param.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeEnum("type", type.fixed, Type.class, EnumDefault.OMIT);
            for (Param param: params)
                param.omitOptionalFieldIfFalse = true;
            g.writeObjectList("params", params, Emptiness.OMIT);
        }
    }

    public static final class Result extends InOutData
    {
        public String caption; ///< optional

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

    public static final class Function extends Serializable
    {
        public boolean arrayParams; ///< optional(false)
        public boolean proprietary; ///< attribute; optional(false)
        public boolean deprecated; ///< attribute; optional(false)
        public String name;
        public String caption; ///< optional
        public List<String> groups;
        public String description; ///< optional
        public String permissions; ///< optional
        public String method; ///< optional
        public String deprecatedDescription = ""; ///< optional
        public InOutData input; ///< optional
        public Result result; ///< optional

        public Function()
        {
            groups = new ArrayList<String>();
            input = new InOutData();
        }

        public boolean areInBodyParameters()
        {
            return method.equals("POST") || method.equals("PUT") || method.equals("PATCH");
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

        protected void readFromParser(Parser p) throws Parser.Error
        {
            proprietary = p.readBooleanAttr("proprietary", BooleanDefault.FALSE);
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
                g.writeBooleanAttr("proprietary", true, BooleanDefault.NONE);

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
