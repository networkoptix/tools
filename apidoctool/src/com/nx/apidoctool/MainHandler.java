package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.SourceCode;
import com.nx.util.SourceCodeEditor;
import com.nx.util.XmlUtils;

import java.io.File;

/**
 * Performs operations on the specified files using other Apidoc mechanisms.
 */
public final class MainHandler
{
    private MainHandler() {}

    public static void sortXml(
        String groupName,
        File inputApiXmlFile,
        File outputApiXmlFile)
        throws Exception
    {
        System.out.println("Sorting group \"" + groupName + "\" in XML file:");
        System.out.println(inputApiXmlFile);

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(inputApiXmlFile));

        ApidocHandler.sortGroup(
            ApidocHandler.getGroupByName(apidoc, groupName));

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);

        System.out.println("SUCCESS: Created .xml file:");
        System.out.println(outputApiXmlFile);
    }

    public static void xmlToCode(
        File sourceApiXmlFile,
        File outputApiXmlFile,
        File connectionFactoryCppFile,
        File outputConnectionFactoryCppFile)
        throws Exception
    {
        System.out.println("Inserting Apidoc from XML to CPP. Input files:");
        System.out.println(sourceApiXmlFile);
        System.out.println(connectionFactoryCppFile);

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(sourceApiXmlFile));

        final SourceCodeEditor editor = new SourceCodeEditor(
            connectionFactoryCppFile);

        final SourceCodeGenerator generator = new SourceCodeGenerator(editor);

        generator.insertCommentsForSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME));

        editor.saveToFile(outputConnectionFactoryCppFile);
        System.out.println("SUCCESS: Created .cpp file:");
        System.out.println(outputConnectionFactoryCppFile);

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);
        System.out.println("SUCCESS: Created .xml file:");
        System.out.println(outputApiXmlFile);
    }

    public static void codeToXml(
        File connectionFactoryCppFile,
        File templateApiXmlFile,
        File outputApiXmlFile)
        throws Exception
    {
        System.out.println(
            "Parsing Apidoc in CPP and inserting to XML. Input files:");
        System.out.println(connectionFactoryCppFile);
        System.out.println(templateApiXmlFile);

        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(XmlUtils.parseXmlDocument(templateApiXmlFile));

        SourceCode reader = new SourceCode(connectionFactoryCppFile);

        SourceCodeParser parser = new SourceCodeParser(reader);

        Apidoc.Group generatedGroup = parser.parseCommentsFromSystemApi(
            ApidocHandler.getGroupByName(apidoc, SYSTEM_API_GROUP_NAME));

        ApidocHandler.replaceFunctions(apidoc, generatedGroup);

        XmlUtils.writeXmlDocument(apidoc.toDocument(), outputApiXmlFile);
        System.out.println("SUCCESS: Created .xml file:");
        System.out.println(outputApiXmlFile);
    }

    //--------------------------------------------------------------------------

    private static final String SYSTEM_API_GROUP_NAME = "System API";
}
