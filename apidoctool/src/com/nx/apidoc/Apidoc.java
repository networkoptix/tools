package com.nx.apidoc;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

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
    }

    public static final class Value extends Serializable
    {
        public String name;
        public String description; ///< optional

        protected void readFromParser(Parser p) throws Parser.Error
        {
            name = p.readString("name", Presence.REQUIRED);
            description = p.readInnerXml("description", Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeString("name", name, Emptiness.PROHIBIT);
            g.writeInnerXml("description", description, Emptiness.ALLOW);
        }
    }

    public static final class Param extends Serializable
    {
        public boolean isGeneratedFromStruct = false;
        public String structName;
        protected boolean omitOptionalFieldIfFalse = false; ///< Used for serializing.

        public boolean unused = false; ///< Internal field, omit param from apidoc.
        public boolean hasDefaultDescription = false; ///< Internal field
        public boolean isRef = false; ///< Internal field

        public boolean proprietary = false; ///< attribute; optional(default=false)
        public boolean readonly = false; ///< attribute; optional(default=false)
        public String name;
        public Type type;
        public String description; ///< optional
        public boolean optional = false; ///< attribute; optional(default=false)
        public List<Value> values; ///< optional

        public Param()
        {
            values = new ArrayList<Value>();
        }

        public void fillMissingFieldsFrom(Param origin)
        {
            if (!isGeneratedFromStruct)
                isGeneratedFromStruct = origin.isGeneratedFromStruct;
            if (structName == null || structName.isEmpty())
                structName = origin.structName;
            if (!omitOptionalFieldIfFalse)
                omitOptionalFieldIfFalse = origin.omitOptionalFieldIfFalse;
            if (!unused)
                unused = origin.unused;
            if (!hasDefaultDescription)
                hasDefaultDescription = origin.hasDefaultDescription;
            if (!proprietary)
                proprietary = origin.proprietary;
            if (!readonly)
                readonly = origin.readonly;
            if (name == null || name.isEmpty())
                name = origin.name;
            if (type == Type.values()[0])
                type = origin.type;
            if (description == null || description.isEmpty())
                description = origin.description;
            if (!optional)
                optional = origin.optional;
            if (values == null || values.isEmpty())
                values = origin.values;
            // TODO: #lbusygin: Merge param values?
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            proprietary = p.readBooleanAttr("proprietary", BooleanDefault.FALSE);
            name = p.readString("name", Presence.REQUIRED);
            type = p.readEnum("type", Type.stringValues, Type.class, Presence.OPTIONAL);
            description = p.readInnerXml("description", Presence.OPTIONAL);
            optional = p.readBoolean("optional", BooleanDefault.FALSE);
            p.readObjectList("values", values, Value.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeBooleanAttr("proprietary", proprietary, BooleanDefault.FALSE);
            g.writeString("name", name, Emptiness.PROHIBIT);
            g.writeEnum("type", type, Type.class, EnumDefault.OMIT);
            g.writeInnerXml("description", description, Emptiness.ALLOW);
            g.writeBoolean("optional", optional,
                omitOptionalFieldIfFalse ? BooleanDefault.FALSE : BooleanDefault.NONE);
            g.writeObjectList("values", values, Emptiness.OMIT);
        }
    }

    public static final class Result extends Serializable
    {
        public String outputStructName;
        public List<Param> unusedParams; ///< Internal field.

        public String caption; ///< optional
        public Type type;
        public List<Param> params; ///< optional

        public Result()
        {
            params = new ArrayList<Param>();
            unusedParams = new ArrayList<Param>();
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            caption = p.readInnerXml("caption", Presence.OPTIONAL);
            type = p.readEnum("type", Type.stringValues, Type.class, Presence.OPTIONAL);
            p.readObjectList("params", params, Param.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeInnerXml("caption", caption, Emptiness.OMIT);
            g.writeEnum("type", type, Type.class, EnumDefault.OMIT);
            for (Param param: params)
                param.omitOptionalFieldIfFalse = true;
            g.writeObjectList("params", params, Emptiness.OMIT);
        }
    }

    public static final class Function extends Serializable
    {
        public List<Param> unusedParams; ///< Internal field.

        public boolean arrayParams; ///< optional(false)
        public boolean proprietary; ///< attribute; optional(false)
        public String name;
        public String caption; ///< optional
        public List<String> groups;
        public String description; ///< optional
        public String permissions; ///< optional
        public String method; ///< optional
        public List<Param> params; ///< optional
        public Result result; ///< optional

        public Function()
        {
            groups = new ArrayList<String>();
            params = new ArrayList<Param>();
            unusedParams = new ArrayList<Param>();
        }

        public boolean isBodyAllowed()
        {
            return !method.equals("GET") && !method.equals("HEAD") && !method.equals("DELETE")
                && !method.equals("CONNECT");
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
            p.readObjectList("params", params, Param.class, Presence.OPTIONAL);
            result = p.readObject("result", Result.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeBooleanAttr("proprietary", proprietary, BooleanDefault.FALSE);
            g.writeBoolean("arrayParams", arrayParams, BooleanDefault.FALSE);
            g.writeString("name", name, Emptiness.PROHIBIT);
            g.writeString("caption", caption, Emptiness.OMIT);
            g.writeInnerXml("description", description, Emptiness.ALLOW);
            g.writeString("permissions", permissions, Emptiness.OMIT);
            g.writeString("method", method, Emptiness.ALLOW);
            g.writeObjectList("params", params, Emptiness.ALLOW);
            g.writeObject("result", result, Emptiness.ALLOW);
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
