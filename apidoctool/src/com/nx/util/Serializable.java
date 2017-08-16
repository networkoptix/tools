package com.nx.util;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Base class for value objects serializable to e.g. XML and JSON. Provides interfaces for
 * serializers to implement. The derived class is expected to have a default constructor.
 */
public abstract class Serializable
{
    //---------------------------------------------------------------------------------------------
    // For serializers.

    /** Override if serialized item name should be different from the lower-case class name. */
    public String getSerializationName()
    {
        return getClass().getSimpleName().toLowerCase();
    }

    public enum Presence { REQUIRED, OPTIONAL }
    public enum EmptyPolicy { PROHIBIT_EMPTY, OMIT_EMPTY, ALLOW_EMPTY }
    public enum BooleanDefault { FALSE, TRUE, NONE }

    /** One instance serializes one object. For inner objects, dedicated instances are created. */
    public interface Generator
    {
        void writeStringAttr(String name, String value, Serializable.EmptyPolicy emptyPolicy);
        void writeBooleanAttr(String name, boolean value, BooleanDefault booleanDefault);
        void writeString(String name, String value, EmptyPolicy mode);
        void writeBoolean(String name, boolean value, BooleanDefault booleanDefault);
        void writeInnerXml(String name, String parentName, String xml);
        void writeObject(String name, Serializable object, EmptyPolicy mode);
        void writeObjectList(String listName, List<? extends Serializable> list, EmptyPolicy mode);
    }

    public interface Parser
    {
        final class Error extends Exception
        {
            public Error(String message, Throwable cause)
            {
                super(message, cause);
            }

            public Error(String message)
            {
                super(message);
            }
        }

        String readStringAttr(String attrName, Presence presence) throws Error;

        boolean readBooleanAttr(String attrName, BooleanDefault booleanDefault) throws Error;

        String readString(String name, Presence presence) throws Error;

        boolean readBoolean(String name, BooleanDefault booleanDefault) throws Error;

        String readInnerXml(String name, String parentName) throws Error;

        <T extends Serializable>
        T readObject(String name, Class<T> objectClass, Presence presence) throws Error;

        <T extends Serializable>
        void readObjectList(
            String listName,
            List<T> list,
            Class<T> objectClass,
            Presence presence) throws Error;
    }

    /** Serializers may store some data on deserialization, and use it for later serialization. */
    public final Map<Class<?>, Object> serializerExtraDataBySerializerClass = new HashMap();

    //---------------------------------------------------------------------------------------------
    // For derived classes.

    /**
     * Base class for value objects which have an inner xml stored as a string. Such objects can
     * have only attribute fields, because, when serialized to XML, all inner elements are bound to
     * the "xml" field.
     */
    public abstract static class WithInnerXml extends Serializable
    {
        public String xml;

        /** Override calling super if there are any attribute fields. */
        protected void readFromParser(Parser p) throws Parser.Error
        {
            xml = p.readInnerXml("xml", getSerializationName());
        }

        /** Override calling super if there are any attribute fields. */
        protected void writeToGenerator(Generator gen)
        {
            gen.writeInnerXml("xml", getSerializationName(), xml);
        }
    }

    /** Implementation should call an appropriate Parser method for each field. */
    protected abstract void readFromParser(Parser p) throws Parser.Error;

    /** Implementation should assign each field with an appropriate Generator method. */
    protected abstract void writeToGenerator(Generator g);
}
