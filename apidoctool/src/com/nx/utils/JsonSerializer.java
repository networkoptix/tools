// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.utils;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;

public final class JsonSerializer
{
    public static JSONObject toJson(Serializable serializable)
    {
        return toJson(serializable, serializable.getSerializationName());
    }

    /**
     * @return The JSON representation of the object; a single-line result will not have a trailing
     * newline, while a multi-line will have a trailing newline.
     */
    public static String toJsonString(Serializable serializable)
    {
        final String result = toJson(serializable).toString(/*indentFactor*/ 2);
        if (result.contains("\n") && !result.endsWith("\n"))
            return result + "\n";
        return result;
    }

    private static JSONObject toJson(Serializable serializable, String name)
    {
        JsonGenerator generator = new JsonGenerator(name);
        serializable.writeToGenerator(generator);
        return generator.json;
    }

    public static <T extends Serializable>
    T fromJsonString(Class<T> objectClass, String jsonString) throws Serializable.Parser.Error
    {
        final T serializable = Utils.createObject(objectClass);

        final JSONObject json;
        try
        {
            json = new JSONObject(jsonString);
        }
        catch (JSONException e)
        {
            throw new Serializable.Parser.Error(
                "Invalid JSON for " + serializable.getSerializationName() + ": " + e.getMessage());
        }

        JsonParser.fromJson(serializable, json, serializable.getSerializationName());

        return serializable;
    }

    //---------------------------------------------------------------------------------------------

    private static final class JsonGenerator implements Serializable.Generator
    {
        private final String parentName;
        private final JSONObject json = new JSONObject();

        /**
         * @param parentName Used for error messages.
         */
        private JsonGenerator(String parentName)
        {
            this.parentName = parentName;
        }

        private boolean omitIfAllowed(
            String name, Serializable.Emptiness emptiness, String valueTypeName)
        {
            switch (emptiness)
            {
                case PROHIBIT:
                    throw new RuntimeException(
                        "INTERNAL ERROR: Required " + valueTypeName + " is empty: " +
                            parentName + "." + name);
                case OMIT:
                    return true;
                default:
                    return false;
            }
        }

        private void writeStringValue(
            String name, String value, Serializable.Emptiness emptiness, String valueTypeName)
        {
            if (value == null)
                value = "";
            if (value.isEmpty() && omitIfAllowed(name, emptiness, valueTypeName))
                return;

            json.put(name, value);
        }

        public void writeBoolean(
            String name, boolean value, Serializable.BooleanDefault booleanDefault)
        {
            if (booleanDefault == Serializable.BooleanDefault.FALSE && value == false)
                return;
            if (booleanDefault == Serializable.BooleanDefault.TRUE && value == true)
                return;
            json.put(name, value);
        }

        public void writeString(String name, String value, Serializable.Emptiness emptiness)
        {
            writeStringValue(name, value, emptiness, "string");
        }

        public void writeInnerXml(String name, String xml, Serializable.Emptiness emptiness)
        {
            if (xml == null)
                xml = "";
            if (xml.isEmpty() && omitIfAllowed(name, emptiness, "xml"))
                return;
            JSONObject objJson = new JSONObject();
            objJson.put("xml", xml);
            json.put(name, objJson);
        }

        public void writeObject(String name, Serializable object, Serializable.Emptiness emptiness)
        {
            JSONObject objJson = toJson(object, parentName + "." + name);
            if (objJson.length() == 0 && omitIfAllowed(name, emptiness, "object"))
                return;
            json.put(name, objJson);
        }

        public void writeEnum(
            String name, Enum value, Class enumClass, Serializable.EnumDefault enumDefault)
        {
            if (value == enumClass.getEnumConstants()[0])
            {
                switch (enumDefault)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required enum value equals default: " +
                                parentName + "." + name);
                    case OMIT:
                        return;
                    default:
                }
            }
            json.put(name, value.toString());
        }

        public void writeObjectList(
            String listName, List<? extends Serializable> list, Serializable.Emptiness emptiness)
        {
            if (list.isEmpty() && omitIfAllowed(listName, emptiness, "list"))
                return;
            JSONArray jsonArray = new JSONArray();
            for (int i = 0; i < list.size(); ++i)
            {
                final Serializable object = list.get(i);
                jsonArray.put(toJson(object, parentName + "." + listName + "[" + i + "]"));
            }
            json.put(listName, jsonArray);
        }
    }

    //---------------------------------------------------------------------------------------------

    private static final class JsonParser implements Serializable.Parser
    {
        private final String parentName;
        private final JSONObject jsonObject;

        private JsonParser(String parentName, JSONObject jsonObject)
        {
            this.parentName = parentName;
            this.jsonObject = jsonObject;
        }

        /**
         * @param jsonObject Can be null, then the object is initialized to its default state.
         * @param parentName Used for error messages.
         */
        private static void fromJson(
            Serializable serializable, JSONObject jsonObject, String parentName)
            throws Error
        {
            JsonParser parser = new JsonParser(parentName, jsonObject);
            serializable.readFromParser(parser);
        }

        private boolean isFieldMissing(
            String name, Serializable.Presence presence, String fieldTypeName) throws Error
        {
            if (jsonObject.opt(name) != null)
                return false;

            if (presence == Serializable.Presence.REQUIRED)
            {
                throw new Error("Required " + fieldTypeName + " field is missing: "
                    + parentName + "." + name);
            }
            return true;
        }

        private String readStringField(
            String name, Serializable.Presence presence, String fieldTypeName) throws Error
        {
            if (jsonObject == null || isFieldMissing(name, presence, fieldTypeName))
                return "";

            final String fullName = parentName + "." + name;

            final String value;
            try
            {
                value = jsonObject.getString(name);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid " + fieldTypeName + " field " + fullName + ": "
                    + e.getMessage());
            }

            if (presence == Serializable.Presence.REQUIRED && value.isEmpty())
                throw new Error("Required " + fieldTypeName + " field is empty: " + fullName);

            return value;
        }

        public String readString(String name, Serializable.Presence presence) throws Error
        {
            return readStringField(name, presence, "string");
        }

        public boolean readBoolean(String name, Serializable.BooleanDefault booleanDefault)
            throws Error
        {
            if (jsonObject == null)
                return false;

            final String fullName = parentName + "." + name;
            if (jsonObject.opt(name) == null)
            {
                if (booleanDefault == Serializable.BooleanDefault.NONE)
                    throw new Error("Required boolean field is missing: " + fullName);
                return booleanDefault == Serializable.BooleanDefault.TRUE;
            }

            try
            {
                return jsonObject.getBoolean(name);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid boolean value in " + fullName + ": "
                    + e.getMessage());
            }
        }

        public String readInnerXml(String name, Serializable.Presence presence) throws Error
        {
            if (jsonObject == null || isFieldMissing(name, presence, "object (xml)"))
                return "";

            final String fullName = parentName + "." + name;

            final JSONObject childJsonObject;
            try
            {
                childJsonObject = jsonObject.getJSONObject(name);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid object (xml) in " + fullName + ": " + e.getMessage());
            }

            if (childJsonObject.opt("xml") == null)
                throw new Error("Required string (xml) field is missing: " + fullName + ".xml");

            final String value;
            try
            {
                value = childJsonObject.getString("xml");
            }
            catch (JSONException e)
            {
                throw new Error("Invalid string (xml) field " + fullName + ".xml: "
                    + e.getMessage());
            }

            if (presence == Serializable.Presence.REQUIRED && value.isEmpty())
                throw new Error("Required string (xml) field is empty: " + fullName + ".xml");

            return value;
        }

        public <T extends Serializable> T readObject(
            String name, Class<T> objectClass, Serializable.Presence presence) throws Error
        {
            final T childObject = Utils.createObject(objectClass);

            if (jsonObject == null || isFieldMissing(name, presence, "object"))
                return childObject;

            final String fullName = parentName + "." + name;

            final JSONObject childJsonObject;
            try
            {
                childJsonObject = jsonObject.getJSONObject(name);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid object in " + fullName + ": " + e.getMessage());
            }

            fromJson(childObject, childJsonObject, fullName);

            return childObject;
        }

        public <E extends Enum<E>>
        E readEnum(
            String name, List<String> values, Class<E> enumClass, Serializable.Presence presence)
            throws Error
        {
            final String stringValue = readStringField(name, presence, "enum");

            if (stringValue.isEmpty())
                return enumClass.getEnumConstants()[0];

            try
            {
                return enumClass.getEnumConstants()[values.indexOf(stringValue)];
            }
            catch (Exception e)
            {
                throw new Error("Invalid enum value \"" + stringValue + "\" in "
                    + parentName + "." + name);
            }
        }

        public <T extends Serializable>
        void readObjectList(
            String listName, List<T> list, Class<T> objectClass, Serializable.Presence presence)
            throws Error
        {
            list.clear();
            if (jsonObject == null || isFieldMissing(listName, presence, "array"))
                return;

            final String listFullName = parentName + "." + listName;

            final JSONArray jsonArray;
            try
            {
                jsonArray = jsonObject.getJSONArray(listName);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid array field " + listFullName + ": " + e.getMessage());
            }

            for (int i = 0; i < jsonArray.length(); ++i)
            {
                final String itemFullName = listFullName + "[" + i + "]";
                final JSONObject childJsonObject;
                try
                {
                    childJsonObject = jsonArray.getJSONObject(i);
                }
                catch (JSONException e)
                {
                    throw new Error("Invalid array item in " + itemFullName + ": "
                        + e.getMessage());
                }

                final T childObject = Utils.createObject(objectClass);
                fromJson(childObject, childJsonObject, itemFullName);
                list.add(childObject);
            }

            if (list.isEmpty() && presence == Serializable.Presence.REQUIRED)
                throw new Error("No array items found in " + listFullName);
        }
    }
}
