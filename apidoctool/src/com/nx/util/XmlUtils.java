package com.nx.util;

import com.sun.org.apache.xml.internal.serialize.OutputFormat;
import com.sun.org.apache.xml.internal.serialize.XMLSerializer;
import org.w3c.dom.*;
import org.xml.sax.InputSource;
import org.xml.sax.SAXException;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;
import java.io.*;

public final class XmlUtils
{
    private XmlUtils() {}

    public static DocumentBuilder createDocumentBuilder()
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

        return documentBuilder;
    }

    public static Document parseXmlDocument(File xmlFile)
        throws IOException, SAXException
    {
        return createDocumentBuilder().parse(xmlFile);
    }

    public static Document parseXmlString(String xmlString)
        throws IOException, SAXException
    {
        InputSource inputSource = new InputSource(new StringReader(xmlString));
        return createDocumentBuilder().parse(inputSource);
    }

    public static String xmlNodeToString(Node node)
    {
        StringWriter writer = new StringWriter();

        OutputFormat format = new OutputFormat();
        format.setLineWidth(80);
        format.setIndenting(true);
        format.setIndent(4);

        XMLSerializer serializer = new XMLSerializer(writer, format);

        try
        {
            serializer.serialize(node);
        }
        catch (IOException e)
        {
            throw new RuntimeException("INTERNAL ERROR", e);
        }

        return writer.toString();
    }

    public static void writeXmlDocument(Document document, File xmlFile)
        throws IOException
    {
        OutputFormat format = new OutputFormat(document);
        format.setLineWidth(80);
        format.setIndenting(true);
        format.setIndent(4);

        FileWriter writer = new FileWriter(xmlFile);
        try
        {
            XMLSerializer serializer = new XMLSerializer(writer, format);

            // Workaround of a known JDK-8081650 bug: processing instructions
            // (often "xml-stylesheet") are serialized in wrong order.
            ProcessingInstruction pi = null;
            Node node = document.getFirstChild();
            if (node instanceof ProcessingInstruction)
            {
                pi = (ProcessingInstruction) node;
                try
                {
                    serializer.processingInstruction(pi.getTarget(), pi.getData());
                }
                catch (SAXException e)
                {
                    throw new RuntimeException("INTERNAL ERROR", e);
                }
                document.removeChild(pi);
            }

            try
            {
                serializer.serialize(document);
            }
            finally
            {
                // Restore the document after workaround.
                if (pi != null)
                    document.insertBefore(pi, document.getFirstChild());
            }
        }
        finally
        {
            writer.close();
        }
    }
}
