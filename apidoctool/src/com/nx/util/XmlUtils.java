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
import java.util.ArrayList;
import java.util.List;

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

    public static Document parseXmlFile(File xmlFile)
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
        format.setIndenting(true);
        format.setIndent(4);
        format.setLineWidth(1000); //< Needed to avoid limit on max indentation.
        format.setOmitXMLDeclaration(true);

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

    public static void writeXmlFile(File xmlFile, Document document)
        throws IOException
    {
        OutputFormat format = new OutputFormat();
        format.setIndenting(true);
        format.setIndent(4);
        format.setLineWidth(1000); //< Needed to avoid limit on max indentation.

        FileWriter writer = new FileWriter(xmlFile);
        try
        {
            XMLSerializer serializer = new XMLSerializer(writer, format);

            // Workaround of a known JDK-8081650 bug: processing instructions
            // (often "xml-stylesheet") are serialized in wrong order.
            List<ProcessingInstruction> processingInstructions = new ArrayList();
            int i = 0;
            while (i < document.getChildNodes().getLength())
            {
                final Node node = document.getChildNodes().item(i);
                if (node instanceof ProcessingInstruction)
                {
                    ProcessingInstruction p = (ProcessingInstruction) node;
                    processingInstructions.add(p);
                    try
                    {
                        serializer.processingInstruction(p.getTarget(), p.getData());
                    }
                    catch (SAXException e)
                    {
                        throw new RuntimeException("INTERNAL ERROR", e);
                    }
                    document.removeChild(p);
                }
                else
                {
                    ++i;
                }
            }

            try
            {
                serializer.serialize(document);
            }
            finally
            {
                // Restore the document after workaround.
                final Node firstNode = document.getFirstChild();
                for (ProcessingInstruction p: processingInstructions)
                    document.insertBefore(p, firstNode);
            }
        }
        finally
        {
            writer.close();
        }
    }
}
