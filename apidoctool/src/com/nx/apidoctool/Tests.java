package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
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

            apiXmlSystemApiFunctionsCount = Integer.valueOf(
                properties.getProperty("apiXmlSystemApiFunctionsCount"));
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
        final File outputCppFile = Utils.insertSuffix(someCppFile, ".TEST");

        SourceCodeEditor sourceCodeEditor = new SourceCodeEditor(someCppFile);

        sourceCodeEditor.saveToFile(outputCppFile);
        checkFileContentsEqual(someCppFile, outputCppFile);

        outputCppFile.delete();
    }

    private void testCppToXml()
        throws Exception
    {
        System.out.println("test: parsing apidoc in C++ and comparing it to the expected XML");
        System.out.println("    Sample: " + apidocXmlFile);
        System.out.println("    Input: " + apidocCppFile);

        SourceCode reader = new SourceCode(apidocCppFile);

        SourceCodeParser parser = new SourceCodeParser(verbose, reader);

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(apidocXmlFile));
        // This apidoc will be used as a sample for the function group - the group content is
        // replaced with the one generated from cpp.

        // Clone the XML file to compare with, for the purpose of normalization.
        final File sampleXmlFile = Utils.insertSuffix(apidocXmlFile, ".TEST");
        XmlUtils.writeXmlFile(sampleXmlFile, XmlSerializer.toDocument(apidoc));

        final Apidoc.Group targetGroup = new Apidoc.Group();
        final Apidoc.Group testGroup = ApidocHandler.getGroupByName(apidoc, APIDOC_TEST_GROUP);
        final int processedFunctionsCount = parser.parseCommentsFromSystemApi(
            testGroup, targetGroup);

        testGroup.functions.clear();
        ApidocHandler.replaceFunctions(apidoc, targetGroup);
        System.out.println("    API functions processed: " + processedFunctionsCount);

        final File outputXmlFile = Utils.insertSuffix(apidocXmlFile, ".OUT");
        XmlUtils.writeXmlFile(outputXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputXmlFile);

        checkFileContentsEqual(outputXmlFile, sampleXmlFile);
    }

    private void testApiXmlToVmsCode()
        throws Exception
    {
        final ApiXmlToVmsCodeExecutor exec = new ApiXmlToVmsCodeExecutor();
        exec.verbose = verbose;
        exec.vmsPath = vmsPath;
        exec.sourceApiXmlFile = apiXmlFile;
        exec.outputApiXmlFile = templateApiXmlFile;

        final int processedFunctionsCount = exec.execute();

        if (apiXmlSystemApiFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiXmlSystemApiFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }
    }

    private void testVmsCodeToApiXml()
        throws Exception
    {
        final VmsCodeToApiXmlExecutor exec = new VmsCodeToApiXmlExecutor();
        exec.verbose = verbose;
        exec.vmsPath = vmsPath;
        exec.templateApiXmlFile = templateApiXmlFile;
        exec.outputApiXmlFile = generatedApiXmlFile;
        exec.outputApiJsonFile = generatedApiJsonFile;

        // This test should parse source files generated by testXmlToCode().
        exec.sourceFileExtraSuffix = Executor.OUTPUT_FILE_EXTRA_SUFFIX;

        final int processedFunctionsCount = exec.execute();

        if (apiXmlSystemApiFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiXmlSystemApiFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }

        checkJsonEqualsXml(generatedApiJsonFile, generatedApiXmlFile);
    }

    private void testOutputApiXmlVsOriginal()
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

    private static final String APIDOC_TEST_GROUP = "testGroup";

    private final boolean verbose;
    private final File testPath;
    private final File someCppFile;
    private final File apidocCppFile;
    private final File apidocXmlFile;
    private final File vmsPath;
    private final File apiXmlFile;
    private final File templateApiXmlFile;
    private final File generatedApiXmlFile;
    private final File generatedApiJsonFile;
    private final File testPropertiesFile;

    private int apiXmlSystemApiFunctionsCount;

    public Tests(boolean verbose, File testPath)
    {
        this.verbose = verbose;
        this.testPath = testPath;
        this.vmsPath = new File(testPath + "/netoptix_vms");
        this.someCppFile = new File(vmsPath + "/appserver2/src/connection_factory.cpp");
        this.apidocCppFile = new File(testPath + "/apidoc.cpp");
        this.apidocXmlFile = new File(testPath + "/apidoc.xml");
        this.apiXmlFile = new File(testPath + "/api.xml");
        this.templateApiXmlFile = Utils.insertSuffix(apiXmlFile, ".TEMPLATE");
        this.generatedApiXmlFile = Utils.insertSuffix(apiXmlFile, ".FROM_CPP");
        this.generatedApiJsonFile = new File(testPath + "/api.FROM_CPP.json");
        this.testPropertiesFile = new File(testPath + "/test.properties");

        readTestProperties();

        run("Xml", new Run() { public void run() throws Exception {
            testXml(); } });

        run("SourceCode", new Run() { public void run() throws Exception {
            testSourceCode(); } });

        run("CppToXml", new Run() { public void run() throws Exception {
            testCppToXml(); } });

        run("ApiXmlToVmsCode", new Run() { public void run() throws Exception {
            testApiXmlToVmsCode(); } });

        run("VmsCodeToApiXml", new Run() { public void run() throws Exception {
            testVmsCodeToApiXml(); } });

        run("OutputXmlVsOriginalXml", new Run() { public void run() throws Exception {
            testOutputApiXmlVsOriginal(); } });

        printFinalMessage();
    }
}
