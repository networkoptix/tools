package com.nx.util;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.util.List;

public final class JsonSerializer
{
    public static final JSONObject toJson(Serializable serializable)
    {
        JsonGenerator generator = new JsonGenerator(serializable.getSerializationName());
        serializable.writeToGenerator(generator);
        return generator.json;
    }

    public static final String toJsonString(Serializable serializable)
    {
        return toJson(serializable).toString(2);
    }

    public static <T extends Serializable>
    T fromJson(Class<T> objectClass, String jsonString) throws Serializable.Parser.Error
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

        JsonParser.fromJson(serializable, json);

        return serializable;
    }

    //---------------------------------------------------------------------------------------------

    private static final class JsonGenerator implements Serializable.Generator
    {
        private final String serializationName;
        private final JSONObject json = new JSONObject();

        private JsonGenerator(String serializationName)
        {
            this.serializationName = serializationName;
        }

        private void writeStringField(
            String name, String value, Serializable.Emptiness emptiness, String fieldTypeName)
        {
            if (value == null)
                value = "";

            if (value.isEmpty())
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required " + fieldTypeName + " is empty: " +
                                serializationName + "." + name);
                    case OMIT:
                        return;
                    default:
                }
            }

            json.put(name, value);
        }

        public void writeStringAttr(
            String name, String value, Serializable.Emptiness emptiness)
        {
            writeStringField(name, value, emptiness, "string attribute");
        }

        public void writeBooleanAttr(
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
            writeStringField(name, value, emptiness, "string");
        }

        public void writeBoolean(
            String name, boolean value, Serializable.BooleanDefault booleanDefault)
        {
            writeBooleanAttr(name, value, booleanDefault);
        }

        public void writeInnerXml(String name, String xml, Serializable.Emptiness emptiness)
        {
            writeStringField(name, xml, emptiness, "xml");
        }

        public void writeObject(
            String name, Serializable object, Serializable.Emptiness emptiness)
        {
            JSONObject objJson = toJson(object);
            if (objJson.length() == 0)
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required JSON object is empty: " +
                                serializationName + "." + name);
                    case OMIT:
                        return;
                    default:
                        // Do nothing.
                }
            }

            json.put(name, objJson);
        }

        public void writeObjectList(
            String listName,
            List<? extends Serializable> list,
            Serializable.Emptiness emptiness)
        {
            if (list.isEmpty())
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required list is empty: " +
                                serializationName + "." + listName);
                    case OMIT:
                        return;
                    default:
                }
            }

            JSONArray jsonArray = new JSONArray();
            for (Serializable object: list)
                jsonArray.put(toJson(object));
            json.put(listName, jsonArray);
        }
    }

    //---------------------------------------------------------------------------------------------

    private static final class JsonParser implements Serializable.Parser
    {
        private final String serializationName;
        private final JSONObject jsonObject;

        private JsonParser(String serializationName, JSONObject jsonObject)
        {
            this.serializationName = serializationName;
            this.jsonObject = jsonObject;
        }

        /** @param jsonObject Can be null, then the object is initialized to its default state. */
        public static void fromJson(Serializable serializable, JSONObject jsonObject) throws Error
        {
            JsonParser parser = new JsonParser(serializable.getSerializationName(), jsonObject);
            serializable.readFromParser(parser);
        }

        private String readStringField(
            String attrName, Serializable.Presence presence, String fieldTypeName) throws Error
        {
            if (jsonObject == null)
                return "";

            if (jsonObject.opt(attrName) == null)
            {
                if (presence == Serializable.Presence.REQUIRED)
                {
                    throw new Error("Required " + fieldTypeName + " field is missing: " +
                        serializationName + "." + attrName);
                }
                return "";
            }

            final String value;
            try
            {
                value = jsonObject.getString(attrName);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid " + fieldTypeName + " field " +
                    serializationName + "." + attrName + ": " + e.getMessage());
            }

            if (presence == Serializable.Presence.REQUIRED && value.isEmpty())
            {
                throw new Error("Required " + fieldTypeName + " field is empty: " +
                    serializationName + "." + attrName);
            }

            return value;
        }

        public String readStringAttr(
            String attrName, Serializable.Presence presence) throws Error
        {
            return readStringField(attrName, presence, "string (attribute)");
        }

        public boolean readBooleanAttr(String attrName, Serializable.BooleanDefault booleanDefault)
        throws Error
        {
            if (jsonObject == null)
                return false;

            if (jsonObject.opt(attrName) == null)
            {
                if (booleanDefault == Serializable.BooleanDefault.NONE)
                {
                    throw new Error("Required boolean field is missing: " +
                        serializationName + "." + attrName);
                }
                return booleanDefault == Serializable.BooleanDefault.TRUE;
            }

            try
            {
                return jsonObject.getBoolean(attrName);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid boolean value in " + serializationName + "." + attrName
                    + ": " + e.getMessage());
            }
        }

        public String readString(String name, Serializable.Presence presence) throws Error
        {
            return readStringField(name, presence, "string");
        }

        public boolean readBoolean(String name, Serializable.BooleanDefault booleanDefault)
            throws Error
        {
            return readBooleanAttr(name, booleanDefault);
        }

        public String readInnerXml(String name, Serializable.Presence presence) throws Error
        {
            return readStringField(name, presence, "string (xml)");
        }

        public <T extends Serializable> T readObject(
            String name, Class<T> objectClass, Serializable.Presence presence) throws Error
        {
            final T childObject = Utils.createObject(objectClass);

            if (jsonObject == null)
                return childObject;

            if (jsonObject.opt(name) == null)
            {
                if (presence == Serializable.Presence.REQUIRED)
                {
                    throw new Error("Required object is missing: "
                        + serializationName + "." + name);
                }
                return childObject;
            }

            JSONObject childJsonObject = null;
            try
            {
                childJsonObject = jsonObject.getJSONObject(name);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid object in " + serializationName + "." + name + ": "
                    + e.getMessage());
            }

            fromJson(childObject, childJsonObject);

            return childObject;
        }

        public <T extends Serializable>
        void readObjectList(
            String listName,
            List<T> list,
            Class<T> objectClass,
            Serializable.Presence presence) throws Error
        {
            list.clear();
            if (jsonObject == null)
                return;

            if (jsonObject.opt(listName) == null)
            {
                if (presence == Serializable.Presence.REQUIRED)
                {
                    throw new Error("Array field not found: " +
                        serializationName + "." + listName);
                }
                return;
            }

            final JSONArray jsonArray;
            try
            {
                jsonArray = jsonObject.getJSONArray(listName);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid array field " + serializationName + "." + listName + ": "
                    + e.getMessage());
            }

            for (int i = 0; i < jsonArray.length(); ++i)
            {
                final JSONObject childJsonObject;
                try
                {
                    childJsonObject = jsonArray.getJSONObject(i);
                }
                catch (JSONException e)
                {
                    throw new Error("Invalid array item in " + serializationName + "." + listName
                        + ": " + e.getMessage());
                }

                final T childObject = Utils.createObject(objectClass);
                fromJson(childObject, childJsonObject);
                list.add(childObject);
            }

            if (list.isEmpty() && presence == Serializable.Presence.REQUIRED)
            {
                throw new Error("No array items found in " +
                    serializationName + "." + listName);
            }
        }
    }
}
