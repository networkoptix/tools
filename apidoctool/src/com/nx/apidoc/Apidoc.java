package com.nx.apidoc;

import java.util.ArrayList;
import java.util.List;

import com.nx.util.Serializable;

/**
 * Object representation of apidoc XML elements. Empty Strings and ArrayLists
 * are used to represent missing values (never null).
 */
public final class Apidoc extends Serializable
{
    public static final class Description extends Serializable.WithInnerXml
    {
        // No fields besides xml.
    }

    public static final class Value extends Serializable
    {
        public String name;
        public Description description; ///< optional

        protected void readFromParser(Parser p) throws Parser.Error
        {
            name = p.readString("name", Presence.REQUIRED);
            description = p.readObject("description", Description.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeString("name", name, EmptyPolicy.PROHIBIT_EMPTY);
            g.writeObject("description", description, EmptyPolicy.ALLOW_EMPTY);
        }
    }

    public static final class Param extends Serializable
    {
        protected boolean omitOptionalFieldIfFalse = false; ///< Used for serializing.

        public boolean proprietary; ///< attribute; optional(default=false)
        public String name;
        public Description description; ///< optional
        public boolean optional; ///< optional(default=false)
        public List<Value> values; ///< optional

        public Param()
        {
            values = new ArrayList<Value>();
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            proprietary = p.readBooleanAttr("proprietary", BooleanDefault.FALSE);
            name = p.readString("name", Presence.REQUIRED);
            description = p.readObject("description", Description.class, Presence.OPTIONAL);
            optional = p.readBoolean("optional", BooleanDefault.FALSE);
            p.readObjectList("values", values, Value.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeBooleanAttr("proprietary", proprietary, BooleanDefault.FALSE);
            g.writeString("name", name, EmptyPolicy.PROHIBIT_EMPTY);
            g.writeObject("description", description, EmptyPolicy.ALLOW_EMPTY);
            g.writeBoolean("optional", optional,
                omitOptionalFieldIfFalse ? BooleanDefault.FALSE : BooleanDefault.NONE);
            g.writeObjectList("values", values, EmptyPolicy.OMIT_EMPTY);
        }
    }

    public static final class Result extends Serializable
    {
        public String caption; ///< optional
        public List<Param> params; ///< optional

        public Result()
        {
            params = new ArrayList<Param>();
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            caption = p.readString("caption", Presence.OPTIONAL);
            p.readObjectList("params", params, Param.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeString("caption", caption, EmptyPolicy.OMIT_EMPTY);
            for (Param param: params)
                param.omitOptionalFieldIfFalse = true;
            g.writeObjectList("params", params, EmptyPolicy.OMIT_EMPTY);
        }
    }

    public static final class Function extends Serializable
    {
        public Group parentGroup;

        public boolean proprietary; ///< attribute; optional(false)
        public String name;
        public String caption; ///< optional
        public Description description; ///< optional
        public String permissions; ///< optional
        public String method; ///< optional
        public List<Param> params; ///< optional
        public Result result; ///< optional

        public Function()
        {
            params = new ArrayList<Param>();
        }

        protected void readFromParser(Parser p) throws Parser.Error
        {
            proprietary = p.readBooleanAttr("proprietary", BooleanDefault.FALSE);
            name = p.readString("name", Presence.REQUIRED);
            caption = p.readString("caption", Presence.OPTIONAL);
            description = p.readObject("description", Description.class, Presence.OPTIONAL);
            permissions = p.readString("permissions", Presence.OPTIONAL);
            method = p.readString("method", Presence.OPTIONAL);
            p.readObjectList("params", params, Param.class, Presence.OPTIONAL);
            result = p.readObject("result", Result.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeBooleanAttr("proprietary", proprietary, BooleanDefault.FALSE);
            g.writeString("name", name, EmptyPolicy.PROHIBIT_EMPTY);
            g.writeString("caption", caption, EmptyPolicy.OMIT_EMPTY);
            g.writeObject("description", description, EmptyPolicy.ALLOW_EMPTY);
            g.writeString("permissions", permissions, EmptyPolicy.OMIT_EMPTY);
            g.writeString("method", method, EmptyPolicy.ALLOW_EMPTY);
            g.writeObjectList("params", params, EmptyPolicy.ALLOW_EMPTY);
            g.writeObject("result", result, EmptyPolicy.ALLOW_EMPTY);
        }
    }

    public static final class Group extends Serializable
    {
        public String groupName;
        public String urlPrefix; ///< optional
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
            groupDescription = p.readString("groupDescription", Presence.REQUIRED);
            p.readObjectList("functions", functions, Function.class, Presence.OPTIONAL);
        }

        protected void writeToGenerator(Generator g)
        {
            g.writeString("groupName", groupName, EmptyPolicy.PROHIBIT_EMPTY);
            g.writeString("urlPrefix", urlPrefix, EmptyPolicy.ALLOW_EMPTY);
            g.writeString("groupDescription", groupDescription, EmptyPolicy.PROHIBIT_EMPTY);
            g.writeObjectList("functions", functions, EmptyPolicy.OMIT_EMPTY);
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
        g.writeObjectList("groups", groups, EmptyPolicy.PROHIBIT_EMPTY);
    }
}
