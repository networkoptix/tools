package com.nx.apidoc;

import com.nx.util.XmlSerializable;
import com.nx.util.XmlUtils;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.xml.sax.SAXException;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

/**
 * Object representation of apidoc XML elements. Empty Strings and ArrayLists
 * are used to represent missing values (never null).
 */
public final class Apidoc extends XmlSerializable
{
    public static final class Description extends XmlSerializable
    {
        public String xml; ///< XHTML content.

        protected boolean arbitraryInnerElementsAllowed()
        {
            return true;
        }

        protected void readFromElement(Element el)
        {
            xml = readInnerXml(el, getElementName());
        }

        protected void writeToElement(Element el)
        {
            appendInnerXml(el, xml);
        }
    }

    public static final class Value extends XmlSerializable
    {
        public String name;
        public Description description; ///< optional

        protected void readFromElement(Element el) throws Error
        {
            name = readString(el, "name", Presence.REQUIRED);
            description = readObj(el, Description.class, Presence.OPTIONAL);
        }

        protected void writeToElement(Element el)
        {
            appendString(el, "name", name, Mode.PROHIBIT_EMPTY);
            appendObj(el, description, Mode.ALLOW_EMPTY);
        }
    }

    public static final class Param extends XmlSerializable
    {
        protected boolean optionalOmitIfFalse = false; ///< Used for XML writing.

        public boolean proprietary; ///< xml-attribute; optional(default=false)
        public String name;
        public Description description; ///< optional
        public boolean optional; ///< optional(default=false)
        public List<Value> values; ///< optional

        public Param()
        {
            values = new ArrayList<Value>();
        }

        protected void readFromElement(Element el) throws Error
        {
            proprietary = readBooleanAttr(el, "proprietary", BooleanDefault.FALSE);
            name = readString(el, "name", Presence.REQUIRED);
            description = readObj(el, Description.class, Presence.OPTIONAL);
            optional = readBoolean(el, "optional", BooleanDefault.FALSE);
            readObjList(el, "values", values, Value.class, Presence.OPTIONAL);
        }

        protected void writeToElement(Element el)
        {
            appendBooleanAttr(el, "proprietary", proprietary, BooleanDefault.FALSE);
            appendString(el, "name", name, Mode.PROHIBIT_EMPTY);
            appendObj(el, description, Mode.ALLOW_EMPTY);
            appendBoolean(el, "optional", optional,
                optionalOmitIfFalse ? BooleanDefault.FALSE : BooleanDefault.NONE);
            appendObjList(el, "values", values, Mode.OMIT_EMPTY);
        }
    }

    public static final class Result extends XmlSerializable
    {
        public String caption; ///< optional
        public List<Param> params; ///< optional

        public Result()
        {
            params = new ArrayList<Param>();
        }

        protected void readFromElement(Element el) throws Error
        {
            caption = readString(el, "caption", Presence.OPTIONAL);
            readObjList(el, "params", params, Param.class, Presence.OPTIONAL);
        }

        protected void writeToElement(Element el)
        {
            appendString(el, "caption", caption, Mode.OMIT_EMPTY);
            for (Param param: params)
                param.optionalOmitIfFalse = true;
            appendObjList(el, "params", params, Mode.OMIT_EMPTY);
        }
    }

    public static final class Function extends XmlSerializable
    {
        public Group parentGroup;

        public boolean proprietary; ///< xml-attribute; optional(false)
        public String name;
        public String caption; ///< optional
        public Description description; ///< optional
        public String method; ///< optional
        public List<Param> params; ///< optional
        public Result result; ///< optional

        public Function()
        {
            params = new ArrayList<Param>();
        }

        protected void readFromElement(Element el) throws Error
        {
            proprietary = readBooleanAttr(el, "proprietary", BooleanDefault.FALSE);
            name = readString(el, "name", Presence.REQUIRED);
            caption = readString(el, "caption", Presence.OPTIONAL);
            description = readObj(el, Description.class, Presence.OPTIONAL);
            method = readString(el, "method", Presence.OPTIONAL);
            readObjList(el, "params", params, Param.class, Presence.OPTIONAL);
            result = readObj(el, Result.class, Presence.OPTIONAL);
        }

        protected void writeToElement(Element el)
        {
            appendBooleanAttr(el, "proprietary", proprietary, BooleanDefault.FALSE);
            appendString(el, "name", name, Mode.PROHIBIT_EMPTY);
            appendString(el, "caption", caption, Mode.OMIT_EMPTY);
            appendObj(el, description, Mode.ALLOW_EMPTY);
            appendString(el, "method", method, Mode.ALLOW_EMPTY);
            appendObjList(el, "params", params, Mode.ALLOW_EMPTY);
            appendObj(el, result, Mode.ALLOW_EMPTY);
        }
    }

    public static final class Group extends XmlSerializable
    {
        public String groupName;
        public String urlPrefix; ///< optional
        public String groupDescription;
        public List<Function> functions; ///< optional

        public Group()
        {
            functions = new ArrayList<Function>();
        }

        protected void readFromElement(Element el) throws Error
        {
            groupName = readString(el, "groupName", Presence.REQUIRED);
            urlPrefix = readString(el, "urlPrefix", Presence.OPTIONAL);
            groupDescription = readString(el, "groupDescription", Presence.REQUIRED);
            readObjList(el, "functions", functions, Function.class, Presence.OPTIONAL);
        }

        protected void writeToElement(Element el)
        {
            appendString(el, "groupName", groupName, Mode.PROHIBIT_EMPTY);
            appendString(el, "urlPrefix", urlPrefix, Mode.ALLOW_EMPTY);
            appendString(el, "groupDescription", groupDescription, Mode.PROHIBIT_EMPTY);
            appendObjList(el, "functions", functions, Mode.OMIT_EMPTY);
        }
    }

    //--------------------------------------------------------------------------

    public List<Group> groups;

    public Apidoc()
    {
        groups = new ArrayList<Group>();
    }

    protected void readFromElement(Element el) throws Error
    {
        readObjList(el, "groups", groups, Group.class, Presence.REQUIRED);
    }

    protected void writeToElement(Element el)
    {
        appendObjList(el, "groups", groups, Mode.PROHIBIT_EMPTY);
    }
}
