// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.utils;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Base class for value objects serializable to e.g. XML and JSON. Provides interfaces for
 * serializers to implement. The derived class is expected to have a default constructor. Each
 * serializable field of the derived class should be manually accessed in the implementation of the
 * abstact methods of this class responsible for (de)serialization - Reflection is not used.
 */
public abstract class Serializable
{
    /** Override if serialized item name should be different from the lower-case class name. */
    public String getSerializationName()
    {
        return getClass().getSimpleName().toLowerCase();
    }

    //---------------------------------------------------------------------------------------------
    // For serializers.

    public enum Presence { REQUIRED, OPTIONAL }
    public enum Emptiness { PROHIBIT, OMIT, ALLOW }
    public enum BooleanDefault { FALSE, TRUE, NONE }

    /** For serialization, first enum value is considered a default value. */
    public enum EnumDefault { PROHIBIT, OMIT, ALLOW }

    public interface Generator
    {
        void writeStringAttr(String name, String value, Emptiness emptiness);
        void writeBooleanAttr(String name, boolean value, BooleanDefault booleanDefault);
        void writeString(String name, String value, Emptiness mode);
        void writeBoolean(String name, boolean value, BooleanDefault booleanDefault);
        void writeInnerXml(String name, String xml, Emptiness emptiness);
        void writeObject(String name, Serializable object, Emptiness mode);
        void writeEnum(String name, Enum value, Class enumClass, EnumDefault enumDefault);
        void writeObjectList(String listName, List<? extends Serializable> list, Emptiness mode);
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
        String readInnerXml(String name, Presence presence) throws Error;

        <T extends Serializable>
        T readObject(String name, Class<T> objectClass, Presence presence) throws Error;

        <E extends Enum<E>>
        E readEnum(
            String name, List<String> values, Class<E> enumClass, Serializable.Presence presence)
            throws Error;

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

    /** Implementation should call an appropriate Parser method for each field. */
    protected abstract void readFromParser(Parser p) throws Parser.Error;

    /** Implementation should assign each field with an appropriate Generator method. */
    protected abstract void writeToGenerator(Generator g);
}
