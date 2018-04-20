package com.nx.util;

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

    public static String toJsonString(Serializable serializable)
    {
        return toJson(serializable).toString(/*indentFactor*/ 2);
    }

    private static JSONObject toJson(Serializable serializable, String name)
    {
        JsonGenerator generator = new JsonGenerator(name);
        serializable.writeToGenerator(generator);
        return generator.json;
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

        public void writeStringAttr(
            String name, String value, Serializable.Emptiness emptiness)
        {
            writeStringValue(name, value, emptiness, "string attribute");
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
            writeStringValue(name, value, emptiness, "string");
        }

        public void writeBoolean(
            String name, boolean value, Serializable.BooleanDefault booleanDefault)
        {
            writeBooleanAttr(name, value, booleanDefault);
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

        private boolean readBooleanField(
            String name, Serializable.BooleanDefault booleanDefault, String fieldTypeName)
            throws Error
        {
            if (jsonObject == null)
                return false;

            final String fullName = parentName + "." + name;
            if (jsonObject.opt(name) == null)
            {
                if (booleanDefault == Serializable.BooleanDefault.NONE)
                    throw new Error("Required " + fieldTypeName + " field is missing: " + fullName);
                return booleanDefault == Serializable.BooleanDefault.TRUE;
            }

            try
            {
                return jsonObject.getBoolean(name);
            }
            catch (JSONException e)
            {
                throw new Error("Invalid " + fieldTypeName + " value in " + fullName + ": "
                    + e.getMessage());
            }
        }

        public String readStringAttr(
            String attrName, Serializable.Presence presence) throws Error
        {
            return readStringField(attrName, presence, "string (attribute)");
        }

        public boolean readBooleanAttr(String attrName, Serializable.BooleanDefault booleanDefault)
            throws Error
        {
            return readBooleanField(attrName, booleanDefault, "boolean (attribute)");
        }

        public String readString(String name, Serializable.Presence presence) throws Error
        {
            return readStringField(name, presence, "string");
        }

        public boolean readBoolean(String name, Serializable.BooleanDefault booleanDefault)
            throws Error
        {
            return readBooleanField(name, booleanDefault, "boolean");
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
