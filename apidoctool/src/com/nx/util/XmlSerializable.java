package com.nx.util;

import org.w3c.dom.*;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Base class for XML-serializable classes. Provides serialization utils.
 * Derived class is expected to have a default constructor.
 */
public abstract class XmlSerializable
{
    public static final class Error
        extends Exception
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

    public String getElementName()
    {
        return getClass().getSimpleName().toLowerCase();
    }

    /**
     * @param element Can be null, in which case the object is initialized to
     * its default state.
     */
    public final void fromElement(Element element) throws Error
    {
        assert processedElNames.isEmpty();

        readFromElement(element);

        if (!arbitraryInnerElementsAllowed())
        {
            // Check for unsupported elements.
            for (Node node = element.getFirstChild(); node != null;
                 node = node.getNextSibling())
            {
                if (node.getNodeType() == Node.ELEMENT_NODE)
                {
                    if (!processedElNames.contains(node.getNodeName()))
                    {
                        throw new Error(
                            "Unsupported element \"" + element.getNodeName() +
                            "." + node.getNodeName() + "\" found.");
                    }
                }
            }

            processedElNames.clear();
        }
    }

    public final void readFromDocument(Document document) throws Error
    {
        Element rootElement = document.getDocumentElement();

        if (!rootElement.getNodeName().equals(getElementName()))
        {
            throw new Error("Root element should have name \"" +
                getElementName() + "\", but is: " +
                rootElement.getNodeName());
        }

        processingInstruction = null;
        Node node = document.getFirstChild();
        if (node instanceof ProcessingInstruction)
            processingInstruction = (ProcessingInstruction) node;

        rootAttributes = rootElement.getAttributes();

        fromElement(rootElement);
    }

    /**
     * @param document Used as a factory to create DOM objects.
     */
    public final Element toElement(Document document)
    {
        Element element = createElement(document);
        writeToElement(element);
        return element;
    }

    public final Document toDocument()
    {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();

        DocumentBuilder documentBuilder = null;
        try
        {
            documentBuilder = factory.newDocumentBuilder();
        }
        catch (ParserConfigurationException e)
        {
            throw new RuntimeException("INTERNAL ERROR", e);
        }

        Document doc = documentBuilder.newDocument();

        if (processingInstruction != null)
        {
            Node importedPi = doc.importNode(processingInstruction, true);
            doc.appendChild(importedPi);
        }

        final Element rootElement = toElement(doc);
        doc.appendChild(rootElement);

        if (rootAttributes != null)
        {
            for (int i = 0; i < rootAttributes.getLength(); ++i)
            {
                Attr node = (Attr) rootAttributes.item(i);
                rootElement.setAttribute(node.getName(), node.getValue());
            }
        }

        return doc;
    }

    /**
     * Can be null. Filled by readDocument() and used by toDocument().
     */
    public ProcessingInstruction processingInstruction;

    /**
     * Can be null. Filled by readDocument() and used by toDocument().
     */
    public NamedNodeMap rootAttributes;

    //--------------------------------------------------------------------------

    protected enum Presence { REQUIRED, OPTIONAL };
    protected enum Mode { PROHIBIT_EMPTY, OMIT_EMPTY, ALLOW_EMPTY };
    protected enum BooleanDefault { FALSE, TRUE, NONE };

    protected final String readStringAttr(
        Element el, String attrName, Presence presence) throws Error
    {
        if (el == null)
            return "";

        String value = el.getAttribute(attrName);
        if (presence == Presence.REQUIRED && value.isEmpty())
        {
            throw new Error("Required attribute is missing or empty: " +
                el.getNodeName() + "." + attrName);
        }

        return value;
    }

    protected final boolean readBooleanAttr(
        Element el, String attrName, BooleanDefault booleanDefault)
        throws Error
    {
        if (el == null)
            return false;

        String value = readStringAttr(el, attrName,
            booleanDefault == BooleanDefault.NONE ?
            Presence.REQUIRED : Presence.OPTIONAL);

        if (value.isEmpty())
        {
            switch (booleanDefault)
            {
                case FALSE: return false;
                case TRUE: return true;
                default: assert false;
            }
        }

        return stringToBoolean(value, el.getNodeName());
    }

    /**
     * Create an object from a single child element. If the element is OPTIONAL
     * and missing, a default object is created.
     * @param parentEl Can be null, in which case a default object is created.
     */
    protected final <T extends XmlSerializable> T readObj(
        Element parentEl, Class<T> objClass, Presence presence) throws Error
    {
        T childObj = createObj(objClass);
        processedElNames.add(childObj.getElementName());
        Element el = null;
        if (parentEl != null)
        {
            el = getSingleChildElement(
                parentEl, childObj.getElementName(), presence);
        }
        childObj.fromElement(el);
        return childObj;
    }

    /**
     * Fill the list with objects created from child elements.
     * @param presence Allows or forbids an empty list.
     */
    protected final <T extends XmlSerializable> void readObjList(
        Element parentEl, String listElementName, List<T> list,
        Class<T> objClass, Presence presence) throws Error
    {
        list.clear();
        if (parentEl == null)
            return;

        processedElNames.add(listElementName);

        final Element listElement = getSingleChildElement(parentEl,
            listElementName, presence);
        if (listElement == null)
        {
            if (presence == Presence.REQUIRED)
            {
                throw new Error("No list element found: " +
                    parentEl.getNodeName() + "." + listElementName);
            }
            return;
        }

        // This object is needed for getElementName().
        T childElement = createObj(objClass);
        final String childElementName = childElement.getElementName();

        for (Node node = listElement.getFirstChild(); node != null;
             node = node.getNextSibling())
        {
            if (node.getNodeType() == Node.ELEMENT_NODE)
            {
                if (!childElementName.equals(node.getNodeName()))
                {
                    throw new Error("Unsupported element \"" + listElementName +
                        "." + node.getNodeName() + "\" found.");
                }

                // Reusing initially created innerElement.
                if (childElement == null)
                    childElement = createObj(objClass);
                childElement.fromElement((Element) node);
                list.add(childElement);
                childElement = null;
            }
        }
        if (list.isEmpty() && presence == Presence.REQUIRED)
        {
            throw new Error("No elements found: " +
                listElementName + "." + childElementName);
        }
    }

    /**
     * Read contents of a single child element with the specified name.
     */
    protected final String readString(
        Element parentEl, String name, Presence presence)
        throws Error
    {
        if (parentEl == null)
            return "";
        processedElNames.add(name);
        Element el = getSingleChildElement(parentEl, name, presence);
        if (el == null)
            return "";

        String value = el.getTextContent();
        if (value.isEmpty() && presence == Presence.REQUIRED)
        {
            throw new Error("Required element is empty: " +
                parentEl.getNodeName() + "." + name);
        }
        return value;
    }

    /**
     * Read contents of a single child element with the specified name.
     */
    protected final boolean readBoolean(
        Element parentEl, String name, BooleanDefault booleanDefault)
        throws Error
    {
        String value = readString(parentEl, name,
            (booleanDefault == BooleanDefault.NONE) ?
            Presence.REQUIRED : Presence.OPTIONAL);
        if (value.isEmpty())
            return (booleanDefault == BooleanDefault.TRUE) ? true : false;
        return stringToBoolean(value, parentEl.getNodeName());
    }

    protected final void appendBooleanAttr(Element el, String name,
        boolean value, BooleanDefault booleanDefault)
    {
        if (booleanDefault == BooleanDefault.FALSE && value == false)
            return;
        if (booleanDefault == BooleanDefault.TRUE && value == true)
            return;
        el.setAttribute(name, Boolean.toString(value));
    }

    protected final void appendString(Element el, String name, String value,
        Mode mode)
    {
        if (value == null)
            value = "";
        if (value.isEmpty())
        {
            switch (mode)
            {
                case PROHIBIT_EMPTY:
                    throw new RuntimeException(
                        "INTERNAL ERROR: Required element value is missing: " +
                        el.getNodeName() + "." + name);
                case OMIT_EMPTY:
                    return;
                default:
                    ;
            }
        }

        Element valueEl = el.getOwnerDocument().createElement(name);
        valueEl.setTextContent(value);
        el.appendChild(valueEl);
    }

    protected final void appendBoolean(
        Element el, String name, boolean value, BooleanDefault booleanDefault)
    {
        if (value == false && booleanDefault == BooleanDefault.FALSE)
            return;
        if (value == true && booleanDefault == BooleanDefault.TRUE)
            return;
        appendString(el, name, Boolean.toString(value), Mode.ALLOW_EMPTY);
    }

    protected final void appendObj(Element el, XmlSerializable obj,
        Mode mode)
    {
        Element valueEl = obj.toElement(el.getOwnerDocument());
        if (valueEl.getFirstChild() == null)
        {
            switch (mode)
            {
                case PROHIBIT_EMPTY:
                    throw new RuntimeException(
                        "INTERNAL ERROR: Required element is empty: " +
                        el.getNodeName() + "." + valueEl.getNodeName());
                case OMIT_EMPTY:
                    return;
                default:
                    ;
            }

        }

        el.appendChild(valueEl);
    }

    protected final <T extends XmlSerializable> void appendObjList(
        Element el, String listElementName, List<T> list, Mode mode)
    {
        if (list.isEmpty())
        {
            switch (mode)
            {
                case PROHIBIT_EMPTY:
                    throw new RuntimeException(
                        "INTERNAL ERROR: Required list is empty: " +
                            el.getNodeName() + "." + listElementName);
                case OMIT_EMPTY:
                    return;
                default:
                    ;
            }
        }

        Element listEl = el.getOwnerDocument().createElement(
            listElementName);
        el.appendChild(listEl);
        for (T obj: list)
            listEl.appendChild(obj.toElement(el.getOwnerDocument()));
    }

    /**
     * @param element Can be null, in which case the object is initialized to
     * its default state.
     */
    protected abstract void readFromElement(Element element) throws Error;

    /**
     * Override with "return true" if no check for unsupported inner elements is
     * required.
     */
    protected boolean arbitraryInnerElementsAllowed()
    {
        return false;
    }

    protected abstract void writeToElement(Element el);

    //--------------------------------------------------------------------------

    private static final <T extends XmlSerializable> T createObj(
        Class<T> objClass)
    {
        try
        {
            return objClass.newInstance();
        }
        catch (InstantiationException e)
        {
            throw new IllegalStateException(e);
        }
        catch (IllegalAccessException e)
        {
            throw new IllegalStateException(e);
        }
    }

    private static final boolean stringToBoolean(String value, String elName)
        throws Error
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
            throw new Error("Invalid boolean value \"" +
                value + "\" in element \"" + elName + "\".");
        }
    }

    private static final Element getSingleChildElement(
        Element parentEl, String name, Presence presence)
        throws Error
    {
        Element result = null;
        for (Node node = parentEl.getFirstChild(); node != null;
             node = node.getNextSibling())
        {
            if (node.getNodeType() == Node.ELEMENT_NODE &&
                name.equals(node.getNodeName()))
            {
                if (result != null)
                {
                    throw new Error("More than one element is found: " +
                        parentEl.getNodeName() + "." + name);
                }
                result = (Element) node;
            }
        }
        if (result == null && presence == Presence.REQUIRED)
        {
            throw new Error("Required element is missing: " +
                parentEl.getNodeName() + "." + name);
        }
        return result;
    }

    private final Element createElement(Document document)
    {
        return document.createElement(getElementName());
    }

    /**
     * Used for checking for unsupported elements on deserialization from XML.
     */
    private final Set<String> processedElNames = new HashSet<String>();
}
