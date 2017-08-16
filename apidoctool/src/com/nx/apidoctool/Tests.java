package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.util.*;
import org.w3c.dom.Document;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.Properties;

public final class Tests extends TestBase
{
    private void readTestProperties()
    {
        Properties properties = new Properties();
        try
        {
            InputStream input = new FileInputStream(testPropertiesFile);
            try
            {
                properties.load(input);
            }
            finally
            {
                input.close();
            }

            expectedProcessedFunctionsCount = Integer.valueOf(
                properties.getProperty("functions_count_SystemApi"));
        }
        catch (Throwable e)
        {
            System.err.println("");
            System.err.println("FATAL ERROR: Unable to read " + testPropertiesFile + ": "
                + e.getMessage());
            System.exit(2);
        }
    }

    private static void apiXmlToXml(File inputXml, File outputXml, File outputJson)
        throws Exception
    {
        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(inputXml));

        final Document outputDocument = XmlSerializer.toDocument(apidoc);
        XmlUtils.writeXmlFile(outputXml, outputDocument);

        final String json = JsonSerializer.toJsonString(apidoc);
        Utils.writeStringToFile(outputJson, json);
    }

    //---------------------------------------------------------------------------------------------

    private void testXml()
        throws Exception
    {
        final File outputXml = Utils.insertSuffix(apiXmlFile, ".TEST");
        final File outputJson = new File(testPath + "/api.TEST.json");

        apiXmlToXml(apiXmlFile, outputXml, outputJson);
        checkFileContentsEqual(apiXmlFile, outputXml);
        checkJsonEqualsXml(outputJson, outputXml);

        outputXml.delete();
        outputJson.delete();
    }

    private void checkJsonEqualsXml(File generatedJson, File originalXml)
        throws Exception
    {
        final File xmlFromJson = Utils.insertSuffix(originalXml, ".FROM_JSON");
        final File strippedXml = Utils.insertSuffix(originalXml, ".STRIPPED");

        final Apidoc apidocFromJson =
            JsonSerializer.fromJson(Apidoc.class, new String(Utils.readAllBytes(generatedJson)));

        XmlUtils.writeXmlFile(xmlFromJson, XmlSerializer.toDocument(apidocFromJson));

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(originalXml));

        apidoc.serializerExtraDataBySerializerClass.clear(); //< Strip data not found in json.

        XmlUtils.writeXmlFile(strippedXml, XmlSerializer.toDocument(apidoc));

        checkFileContentsEqual(xmlFromJson, strippedXml);

        xmlFromJson.delete();
        strippedXml.delete();
    }

    private void testSourceCode()
        throws Exception
    {
        final File outputCppFile = Utils.insertSuffix(cppFile, ".TEST");

        SourceCodeEditor sourceCodeEditor = new SourceCodeEditor(cppFile);

        sourceCodeEditor.saveToFile(outputCppFile);
        TestBase.checkFileContentsEqual(cppFile, outputCppFile);

        outputCppFile.delete();
    }

    private void testXmlToCode()
        throws Exception
    {
        final XmlToCodeExecutor exec = new XmlToCodeExecutor();
        exec.vmsPath = vmsPath;
        exec.sourceApiXmlFile = apiXmlFile;
        exec.outputApiXmlFile = templateApiXmlFile;

        final int processedFunctionsCount = exec.execute();

        if (expectedProcessedFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + expectedProcessedFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }
    }

    private void testCodeToXml()
        throws Exception
    {
        final CodeToXmlExecutor exec = new CodeToXmlExecutor();
        exec.vmsPath = vmsPath;
        exec.templateApiXmlFile = templateApiXmlFile;
        exec.outputApiXmlFile = generatedApiXmlFile;
        exec.outputApiJsonFile = generatedApiJsonFile;

        // This test should parse source files generated by testXmlToCode().
        exec.sourceFileExtraSuffix = Executor.OUTPUT_FILE_EXTRA_SUFFIX;

        final int processedFunctionsCount = exec.execute();

        if (expectedProcessedFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + expectedProcessedFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }

        checkJsonEqualsXml(generatedApiJsonFile, generatedApiXmlFile);
    }

    private void outputXmlVsOriginalXml()
        throws Exception
    {
        final File sortedApiXmlFile = Utils.insertSuffix(apiXmlFile, ".SORTED");

        final XmlSorter sorter = new XmlSorter();
        sorter.groupName = Executor.SYSTEM_API_GROUP_NAME;
        sorter.sourceApiXmlFile = apiXmlFile;
        sorter.outputApiXmlFile = sortedApiXmlFile;
        sorter.execute();

        checkTextFilesEqualIgnoringIndents(
            sortedApiXmlFile, generatedApiXmlFile);
    }

    //---------------------------------------------------------------------------------------------

    private final File testPath;
    private final File vmsPath;
    private final File apiXmlFile;
    private final File templateApiXmlFile;
    private final File generatedApiXmlFile;
    private final File generatedApiJsonFile;
    private final File cppFile;
    private final File testPropertiesFile;

    private int expectedProcessedFunctionsCount;

    public Tests(File testPath)
    {
        this.testPath = testPath;
        this.vmsPath = new File(testPath + "/netoptix_vms");
        this.apiXmlFile = new File(testPath + "/api.xml");
        this.templateApiXmlFile = Utils.insertSuffix(apiXmlFile, ".TEMPLATE");
        this.generatedApiXmlFile = Utils.insertSuffix(apiXmlFile, ".FROM_CPP");
        this.generatedApiJsonFile = new File(testPath + "/api.FROM_CPP.json");
        this.cppFile = new File(vmsPath + "/appserver2/src/connection_factory.cpp");
        this.testPropertiesFile = new File(testPath + "/test.properties");

        readTestProperties();

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
