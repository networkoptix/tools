package com.nx.util;

import org.w3c.dom.*;
import org.xml.sax.SAXException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.io.IOException;
import java.util.*;

public final class XmlSerializer
{

    public static Document toDocument(Serializable serializable)
    {
        return XmlGenerator.toDocument(serializable);
    }

    public static <T extends Serializable>
    T fromDocument(Class<T> objectClass, Document document)
        throws Serializable.Parser.Error
    {
        T serializable = Utils.createObject(objectClass);

        Element rootElement = document.getDocumentElement();

        if (!rootElement.getNodeName().equals(serializable.getSerializationName()))
        {
            throw new Serializable.Parser.Error("Root element should have name \"" +
                serializable.getSerializationName() + "\", but is: " +
                rootElement.getNodeName());
        }

        ExtraData extraData = new ExtraData();
        serializable.serializerExtraDataBySerializerClass.put(XmlSerializer.class, extraData);

        for (int i = 0; i < document.getChildNodes().getLength(); ++i)
        {
            final Node node = document.getChildNodes().item(i);
            if (node instanceof ProcessingInstruction)
                extraData.processingInstructions.add((ProcessingInstruction) node);
        }

        for (int i = 0; i < rootElement.getAttributes().getLength(); ++i)
        {
            final Node attribute = rootElement.getAttributes().item(i);
            if (attribute.getNodeName().matches(ExtraData.rootAttributeRegex))
            {
                extraData.rootAttributes.add(new AbstractMap.SimpleEntry<String, String>(
                    attribute.getNodeName(), attribute.getNodeValue()));
            }
        }

        XmlParser.fromElement(serializable, rootElement);

        return serializable;
    }

    //---------------------------------------------------------------------------------------------

    /** Data transparently kept in XML file: read by fromDocument(), output by toDocument(). */
    private static final class ExtraData
    {
        /** Processing instructions which follow <?xml>, if any. */
        public final List<ProcessingInstruction> processingInstructions =
            new ArrayList<ProcessingInstruction>();

        public static final String rootAttributeRegex = "xmlns:.*|xsi:.*";

        /** Ordered list of root element attributes which names match rootAttributeRegex. */
        public final List<Map.Entry<String, String>> rootAttributes =
            new ArrayList<Map.Entry<String, String>>();
    }

    //---------------------------------------------------------------------------------------------

    /** One instance serializes one object. For inner objects, dedicated instances are created. */
    private static final class XmlGenerator implements Serializable.Generator
    {
        private final Element element;

        private XmlGenerator(Element element)
        {
            this.element = element;
        }

        /**
         * @param document Used as a factory to create DOM objects.
         */
        private static Element toElement(Serializable serializable, String name, Document document)
        {
            XmlGenerator generator = new XmlGenerator(document.createElement(name));
            serializable.writeToGenerator(generator);
            return generator.element;
        }

        public static Document toDocument(Serializable serializable)
        {
            final ExtraData extraData = (ExtraData)
                serializable.serializerExtraDataBySerializerClass.get(XmlSerializer.class);

            final DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();

            final DocumentBuilder documentBuilder;
            try
            {
                documentBuilder = factory.newDocumentBuilder();
            }
            catch (ParserConfigurationException e)
            {
                throw new RuntimeException("INTERNAL ERROR", e);
            }

            final Document document = documentBuilder.newDocument();

            if (extraData != null)
            {
                for (ProcessingInstruction processingInstruction: extraData.processingInstructions)
                {
                    final Node importedProcessingInstruction = document.importNode(
                        processingInstruction, /*deep*/ true);
                    document.appendChild(importedProcessingInstruction);
                }
            }

            final Element rootElement = toElement(
                serializable, serializable.getSerializationName(), document);
            document.appendChild(rootElement);

            if (extraData != null)
            {
                for (Map.Entry<String, String> attribute: extraData.rootAttributes)
                    rootElement.setAttribute(attribute.getKey(), attribute.getValue());
            }

            return document;
        }

        public final void writeStringAttr(
            String name, String value, Serializable.Emptiness emptiness)
        {
            if (value == null)
                value = "";

            if (value.isEmpty())
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required string attribute is empty: " +
                                element.getNodeName() + "." + name);
                    case OMIT:
                        return;
                    default:
                }
            }

            element.setAttribute(name, value);
        }

        public final void writeBooleanAttr(
            String name, boolean value, Serializable.BooleanDefault booleanDefault)
        {
            if (booleanDefault == Serializable.BooleanDefault.FALSE && value == false)
                return;
            if (booleanDefault == Serializable.BooleanDefault.TRUE && value == true)
                return;
            element.setAttribute(name, Boolean.toString(value));
        }

        public void writeString(String name, String value, Serializable.Emptiness emptiness)
        {
            if (value == null)
                value = "";
            if (value.isEmpty())
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required string value is empty: " +
                                element.getNodeName() + "." + name);
                    case OMIT:
                        return;
                    default:
                }
            }

            Element valueElement = element.getOwnerDocument().createElement(name);
            valueElement.setTextContent(value);
            element.appendChild(valueElement);
        }

        public void writeBoolean(
            String name, boolean value, Serializable.BooleanDefault booleanDefault)
        {
            if (value == false && booleanDefault == Serializable.BooleanDefault.FALSE)
                return;
            if (value == true && booleanDefault == Serializable.BooleanDefault.TRUE)
                return;
            writeString(name, Boolean.toString(value), Serializable.Emptiness.ALLOW);
        }

        /**
         * Parse XML string to a list of inner elements.
         */
        public void writeInnerXml(String name, String xml, Serializable.Emptiness emptiness)
        {
            if (xml == null)
                xml = "";

            if (xml.isEmpty())
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required inner-xml value is empty: " +
                                element.getNodeName() + "." + name);
                    case OMIT:
                        return;
                    default:
                }
            }

            final Document doc;
            try
            {
                doc = XmlUtils.parseXmlString("<xml>" + xml + "</xml>");
            }
            catch (IOException e)
            {
                throw new RuntimeException(
                    "INTERNAL ERROR: Failed to parse <" + name + "> string as XML:\n" + xml, e);
            }
            catch (SAXException e)
            {
                throw new RuntimeException(
                    "INTERNAL ERROR: Failed to parse <" + name + "> string as XML:\n" + xml, e);
            }

            Element valueElement = element.getOwnerDocument().createElement(name);

            final Element rootElement = doc.getDocumentElement();
            for (Node node = rootElement.getFirstChild(); node != null;
                 node = node.getNextSibling())
            {
                final Node importedNode =
                    element.getOwnerDocument().importNode(node, /*deep*/ true);
                valueElement.appendChild(importedNode);
            }

            element.appendChild(valueElement);
        }

        public void writeObject(
            String name, Serializable object, Serializable.Emptiness emptiness)
        {
            final Element valueElement = toElement(object, name, element.getOwnerDocument());
            if (valueElement.getFirstChild() == null)
            {
                switch (emptiness)
                {
                    case PROHIBIT:
                        throw new RuntimeException(
                            "INTERNAL ERROR: Required element is empty: " +
                                element.getNodeName() + "." + valueElement.getNodeName());
                    case OMIT:
                        return;
                    default:
                }

            }

            element.appendChild(valueElement);
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
                                 element.getNodeName() + "." + name);
                    case OMIT:
                        return;
                    default:
                }
            }

            Element valueElement = element.getOwnerDocument().createElement(name);
            valueElement.setTextContent(value.toString());
            element.appendChild(valueElement);
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
                                element.getNodeName() + "." + listName);
                    case OMIT:
                        return;
                    default:
                }
            }

            final Element listElement = element.getOwnerDocument().createElement(listName);
            element.appendChild(listElement);
            for (Serializable object: list)
            {
                listElement.appendChild(
                    toElement(object, object.getSerializationName(), element.getOwnerDocument()));
            }
        }
    }

    //---------------------------------------------------------------------------------------------

    /** One instance serializes one object. For inner objects, dedicated instances are created. */
    private static final class XmlParser implements Serializable.Parser
    {
        private final String serializationName;
        private final Element element;

        /** Used for checking for unsupported elements on deserialization from XML. */
        private final Set<String> processedElementNames = new HashSet<String>();

        private XmlParser(String serializationName, Element element)
        {
            this.serializationName = serializationName;
            this.element = element;
        }

        /** @param element Can be null, then the object is initialized to its default state. */
        public static void fromElement(Serializable serializable, Element element) throws Error
        {
            final XmlParser parser = new XmlParser(serializable.getSerializationName(), element);
            serializable.readFromParser(parser);
            parser.checkForUnsupportedElements();
        }

        public String readStringAttr(
            String attrName, Serializable.Presence presence) throws Error
        {
            if (element == null)
                return "";

            final String value = element.getAttribute(attrName);

            if (presence == Serializable.Presence.REQUIRED && value.isEmpty())
            {
                throw new Error("Required attribute is missing or empty: " +
                    element.getNodeName() + "." + attrName);
            }

            return value;
        }

        public boolean readBooleanAttr(String attrName, Serializable.BooleanDefault booleanDefault)
            throws Error
        {
            if (element == null)
                return false;

            final String value = readStringAttr(attrName,
                (booleanDefault == Serializable.BooleanDefault.NONE)
                    ? Serializable.Presence.REQUIRED
                    : Serializable.Presence.OPTIONAL);

            if (value.isEmpty())
            {
                switch (booleanDefault)
                {
                    case FALSE: return false;
                    case TRUE: return true;
                    default: assert false;
                }
            }

            return stringToBoolean(value, element.getNodeName());
        }

        /** Read contents of a single child element with the specified name. */
        public String readString(String name, Serializable.Presence presence) throws Error
        {
            if (element == null)
                return "";

            processedElementNames.add(name);

            final Element childElement = getSingleChildElement(element, name, presence);
            if (childElement == null)
                return "";

            final String value = childElement.getTextContent();

            if (value.isEmpty() && presence == Serializable.Presence.REQUIRED)
            {
                throw new Error("Required element is empty: " +
                    element.getNodeName() + "." + name);
            }

            return value;
        }

        public boolean readBoolean(String name, Serializable.BooleanDefault booleanDefault)
            throws Error
        {
            if (element == null)
                return false;

            final String value = readString(name,
                (booleanDefault == Serializable.BooleanDefault.NONE)
                    ? Serializable.Presence.REQUIRED
                    : Serializable.Presence.OPTIONAL);

            if (value.isEmpty())
                return booleanDefault == Serializable.BooleanDefault.TRUE;

            return stringToBoolean(value, name);
        }

        public String readInnerXml(String name, Serializable.Presence presence)
            throws Error
        {
            if (element == null)
                return "";

            processedElementNames.add(name);

            final Element childElement = getSingleChildElement(element, name, presence);
            if (childElement == null)
                return "";

            final String xml = XmlUtils.xmlNodeToString(childElement).trim();
            if (xml.equals("<" + name + "/>"))
                return "";

            // Trim opening and closing tags, since only contents is needed.
            final int openingTagLen = ("<" + name + ">").length();
            final int closingTagLen = ("</" + name + ">").length();
            return xml.substring(openingTagLen, xml.length() - closingTagLen);
        }

        /**
         * Create an object from a single child element. If the element is OPTIONAL and missing, a
         * default object is created. If element field, which is the parent xml element, is null, a
         * default object is created.
         */
        public <T extends Serializable>
        T readObject(
            String name, Class<T> objectClass, Serializable.Presence presence) throws Error
        {
            final T childObject = Utils.createObject(objectClass);
            processedElementNames.add(name);
            Element childElement = null;
            if (element != null)
                childElement = getSingleChildElement(element, name, presence);
            fromElement(childObject, childElement);
            return childObject;
        }

        public <E extends Enum<E>>
        E readEnum(
            String name, List<String> values, Class<E> enumClass, Serializable.Presence presence)
            throws Error
        {
            final String stringValue = readString(name, presence);

            if (stringValue.isEmpty())
                return enumClass.getEnumConstants()[0];

            try
            {
                return enumClass.getEnumConstants()[values.indexOf(stringValue)];
            }
            catch (Exception e)
            {
                throw new Error("Invalid enum value \"" + stringValue + "\" in element "
                    + element.getNodeName() + "." + name);
            }
        }

        public <T extends Serializable>
        void readObjectList(
            String listName, List<T> list,
            Class<T> objectClass,
            Serializable.Presence presence) throws Error
        {
            list.clear();
            if (element == null)
                return;

            processedElementNames.add(listName);

            final Element listElement = getSingleChildElement(element, listName, presence);
            if (listElement == null)
            {
                if (presence == Serializable.Presence.REQUIRED)
                {
                    throw new Error("List element not found: " +
                        element.getNodeName() + "." + listName);
                }
                return;
            }

            // This object is needed for getSerializationName().
            T childObject = Utils.createObject(objectClass);
            final String childElementName = childObject.getSerializationName();

            for (Node node = listElement.getFirstChild(); node != null;
                 node = node.getNextSibling())
            {
                if (node.getNodeType() == Node.ELEMENT_NODE)
                {
                    if (!childElementName.equals(node.getNodeName()))
                    {
                        throw new Error("Unsupported element " + listName +
                            "." + node.getNodeName() + " found.");
                    }

                    // Reusing initially created innerElement.
                    if (childObject == null)
                        childObject = Utils.createObject(objectClass);
                    fromElement(childObject, (Element) node);
                    list.add(childObject);
                    childObject = null;
                }
            }

            if (list.isEmpty() && presence == Serializable.Presence.REQUIRED)
            {
                throw new Error("No list items found: " +
                    serializationName + "." + listName + "." + childElementName);
            }
        }

        private void checkForUnsupportedElements() throws Error
        {
            if (element == null)
                return;

            for (Node node = element.getFirstChild(); node != null; node = node.getNextSibling())
            {
                if (node.getNodeType() == Node.ELEMENT_NODE)
                {
                    if (!processedElementNames.contains(node.getNodeName()))
                    {
                        throw new Error("Unsupported element " + element.getNodeName() +
                            "." + node.getNodeName() + " found.");
                    }
                }
            }
        }

        private static Element getSingleChildElement(
            Element parentElement, String name, Serializable.Presence presence) throws Error
        {
            Element result = null;
            for (Node node = parentElement.getFirstChild(); node != null;
                 node = node.getNextSibling())
            {
                if (node.getNodeType() == Node.ELEMENT_NODE &&
                    name.equals(node.getNodeName()))
                {
                    if (result != null)
                    {
                        throw new Error("More than one element is found: " +
                            parentElement.getNodeName() + "." + name);
                    }
                    result = (Element) node;
                }
            }
            if (result == null && presence == Serializable.Presence.REQUIRED)
            {
                throw new Error("Required element is missing: " +
                    parentElement.getNodeName() + "." + name);
            }
            return result;
        }

        private boolean stringToBoolean(String value, String name) throws Error
        {
            if ("0".equals(value) || "false".equals(value))
            {
                return false;
            }
            else if ("1".equals(value) || "true".equals(value))
            {
                return true;
            }
            else
            {
                throw new Error("Invalid boolean value \""
                    + value + "\" in element " + element.getNodeName()+ "." + name);
            }
        }
    }
}
