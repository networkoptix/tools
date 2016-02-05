package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.util.SourceCodeEditor;
import com.nx.util.TestBase;
import com.nx.util.XmlUtils;
import org.w3c.dom.Document;

import java.io.File;

public final class Tests
    extends TestBase
{
    private static void xmlToXml(File inputApiXmlFile, File outputApiXmlFile)
        throws Exception
    {
        final Document document = XmlUtils.parseXmlDocument(inputApiXmlFile);
        final Apidoc apidoc = new Apidoc();
        apidoc.readFromDocument(document);
        final Document outputDocument = apidoc.toDocument();
        XmlUtils.writeXmlDocument(outputDocument, outputApiXmlFile);
    }

    //--------------------------------------------------------------------------

    private void testXml()
        throws Exception
    {
        final File apiXmlFile = new File(testPath + "/api.xml");

        final File outputXmlFile = new File(testPath + "/api_TEST_OUT.xml");

        final File newOutputXmlFile = new File(
            testPath + "/api_TEST_OUT_NEW.xml");

        xmlToXml(apiXmlFile, outputXmlFile);
        TestBase.checkFileContentsEqual(apiXmlFile, outputXmlFile);

        xmlToXml(outputXmlFile, newOutputXmlFile);
        TestBase.checkFileContentsEqual(outputXmlFile, newOutputXmlFile);

        outputXmlFile.delete();
        newOutputXmlFile.delete();
    }

    private void testSourceCode()
        throws Exception
    {
        final File cppFile = new File(testPath + "/connection_factory.cpp");

        final File outputCppFile = new File(
            testPath + "/connection_factory_TEST_OUT.cpp");

        SourceCodeEditor sourceCodeEditor = new SourceCodeEditor(cppFile);

        sourceCodeEditor.saveToFile(outputCppFile);
        TestBase.checkFileContentsEqual(cppFile, outputCppFile);

        outputCppFile.delete();
    }

    private void testXmlToCode()
        throws Exception
    {
        final File sourceApiXmlFile = new File(testPath + "/api.xml");

        final File outputApiXmlFile = new File(testPath + "/api_TEMPLATE.xml");

        final File connectionFactoryCppFile = new File(
            testPath + "/connection_factory.cpp");

        final File outputConnectionFactoryCppFile = new File(
            testPath + "/connection_factory_FROM_XML.cpp");

        MainHandler.xmlToCode(sourceApiXmlFile, outputApiXmlFile,
            connectionFactoryCppFile, outputConnectionFactoryCppFile);
    }

    private void testCodeToXml()
        throws Exception
    {
        final File templateApiXmlFile = new File(testPath + "/api_TEMPLATE.xml");

        final File outputXmlFile = new File(testPath + "/api_FROM_CPP.xml");

        final File connectionFactoryCppFile = new File(
            testPath + "/connection_factory_FROM_XML.cpp");

        MainHandler.codeToXml(
            connectionFactoryCppFile, templateApiXmlFile, outputXmlFile);
    }

    private void outputXmlVsOriginalXml()
        throws Exception
    {
        final File apiXmlFile = new File(testPath + "/api.xml");
        final File outputXmlFile = new File(testPath + "/api_FROM_CPP.xml");

        checkTextFileEqualIgnoringIndents(apiXmlFile, outputXmlFile);
    }

    //--------------------------------------------------------------------------

    private File testPath;
    
    public Tests(File testPath)
    {
        this.testPath = testPath;

        run("testXml", new Run() { public void run() throws Exception {
            testXml(); } });

        run("testSourceCode", new Run() { public void run() throws Exception {
            testSourceCode(); } });

        run("xmlToCode", new Run() { public void run() throws Exception {
            testXmlToCode(); } });

        run("codeToXml", new Run() { public void run() throws Exception {
            testCodeToXml(); } });

        run("outputXmlVsOriginalXml", new Run() { public void run() throws Exception {
            outputXmlVsOriginalXml(); } });

        printFinalMessage();
    }
}
