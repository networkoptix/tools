package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
import com.nx.apidoc.ApidocHandler;
import com.nx.util.*;
import org.w3c.dom.Document;

import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.util.*;

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

    private static void assertJsonEqualsXml(File apiJson, File apiXml)
        throws Exception
    {
        final File xmlFromJsonFile = Utils.replaceExtension(apiJson, ".FROM_JSON.xml");
        final File strippedXmlFile = Utils.insertSuffix(apiXml, ".STRIPPED");

        final Apidoc apidocFromJson =
            JsonSerializer.fromJson(Apidoc.class, new String(Utils.readAllBytes(apiJson)));

        XmlUtils.writeXmlFile(xmlFromJsonFile, XmlSerializer.toDocument(apidocFromJson));

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(apiXml));

        apidoc.serializerExtraDataBySerializerClass.clear(); //< Strip data not found in json.

        XmlUtils.writeXmlFile(strippedXmlFile, XmlSerializer.toDocument(apidoc));

        assertFileContentsEqual(xmlFromJsonFile, strippedXmlFile);
    }

    //---------------------------------------------------------------------------------------------

    private static final class TestParams
        extends ParamsBase
    {
        public String stringParam()
        {
            return stringParam.toString();
        }

        private final StringBuilder stringParam = regStringParam("stringParam",
            "default value", "Test string value.");
    }

    private void testParamsBaseInvalidArg(ParamsBase params, String arg)
        throws Exception
    {
        boolean testFailed = false;
        try
        {
            params.parse(/*optionalFile*/ null, Arrays.asList(arg), /*verbose*/ true);
            testFailed = true;
        }
        catch (RuntimeException e)
        {
            // OK.
        }
        if (testFailed)
            throw new Exception("Invalid arg [" + arg + "] accepted by Params.");
    }

    private void testParamsBase()
        throws Exception
    {
        final TestParams params = new TestParams();
        assertEquals("default value", params.stringParam());
        params.printHelp(System.out, "    ");

        testParamsBaseInvalidArg(params, "-Dunknown=value");
        testParamsBaseInvalidArg(params, "-D=missingName");
        testParamsBaseInvalidArg(params, "-DstringParam");
        testParamsBaseInvalidArg(params, "noMinusD");

        final String stringValue = "Value with 2 spaces,\\backslash,\ttab,\nnewline";

        params.parse(
            /*optionalFile*/ null,
            Arrays.asList("-DstringParam=" + stringValue),
            /*verbose*/ true);
        assertEquals(stringValue, params.stringParam());

        params.stringParam.setLength(0);

        final List<String> testFileText = Arrays.asList(
            "stringParam=Value with 2 spaces,\\\\backslash,\\ttab,\\nnewline",
            "# End of file");

        final File testFile = new File(outputTestPath + "/params.properties");
        Utils.writeStringListToFile(testFile, testFileText, /*lineBreak*/ "\n");
        params.parse(testFile, Collections.<String>emptyList(), /*verbose*/ false);

        assertEquals(stringValue, params.stringParam());
    }

    private void testXml()
        throws Exception
    {
        apiXmlToXml(apiXmlFile, outputApiXmlFile, outputApiJsonFile);

        assertFileContentsEqual(apiXmlFile, outputApiXmlFile);
        assertJsonEqualsXml(outputApiJsonFile, outputApiXmlFile);
    }

    private void testSourceCodeEditor()
        throws Exception
    {
        final SourceCodeEditor sourceCodeEditor = new SourceCodeEditor(cppFile);
        sourceCodeEditor.saveToFile(outputCppFile);

        assertFileContentsEqual(cppFile, outputCppFile);
    }

    private void testSourceCodeParser()
        throws Exception
    {
        System.out.println("test: parsing apidoc in C++ and comparing it to the expected XML");
        System.out.println("    Sample: " + apidocXmlFile);
        System.out.println("    Input: " + apidocCppFile);

        // This apidoc will be used as a sample for the function group - the group content is
        // replaced with the one generated from cpp.
        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(apidocXmlFile));

        // Clone the XML file to compare with, for the purpose of normalization.
        XmlUtils.writeXmlFile(normalizedApidocXmlFile, XmlSerializer.toDocument(apidoc));

        // apidocCppFile -> targetGroup: parse C++ code, generate apidoc group.
        final Apidoc.Group targetGroup = new Apidoc.Group();
        final Apidoc.Group sourceGroup = ApidocHandler.getGroupByName(apidoc, "testGroup");
        final SourceCode reader = new SourceCode(apidocCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount =
            sourceCodeParser.parseCommentsFromSystemApi(sourceGroup, targetGroup);
        System.out.println("    API functions processed: " + processedFunctionsCount);

        // Replace in apidoc the original group with the generated one.
        sourceGroup.functions.clear();
        ApidocHandler.replaceFunctions(apidoc, targetGroup);

        XmlUtils.writeXmlFile(outputApidocXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApidocXmlFile);

        assertFileContentsEqual(outputApidocXmlFile, normalizedApidocXmlFile);
    }

    private void testApiXmlToVmsCode()
        throws Exception
    {
        final ApiXmlToVmsCodeExecutor executor = new ApiXmlToVmsCodeExecutor();
        executor.verbose = verbose;
        executor.vmsPath = vmsPath;
        executor.optionalOutputVmsPath = outputVmsPath;
        executor.sourceApiXmlFile = apiXmlFile;
        executor.outputApiXmlFile = templateApiXmlFile;
        executor.params = new Params();

        final int processedFunctionsCount = executor.execute();

        if (apiXmlSystemApiFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiXmlSystemApiFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }
    }

    private void testVmsCodeToApiXml()
        throws Exception
    {
        // This test should parse source files generated by testXmlToCode().

        final VmsCodeToApiXmlExecutor executor = new VmsCodeToApiXmlExecutor();
        executor.verbose = verbose;
        executor.vmsPath = outputVmsPath;
        executor.sourceFileExtraSuffix = Executor.OUTPUT_FILE_EXTRA_SUFFIX;
        executor.templateApiXmlFile = templateApiXmlFile;
        executor.outputApiXmlFile = generatedApiXmlFile;
        executor.optionalOutputApiJsonFile = generatedApiJsonFile;
        executor.params = new Params();

        final int processedFunctionsCount = executor.execute();

        if (apiXmlSystemApiFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiXmlSystemApiFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }

        assertJsonEqualsXml(generatedApiJsonFile, generatedApiXmlFile);
    }

    private void testOutputApiXmlVsOriginal()
        throws Exception
    {
        final XmlSorter sorter = new XmlSorter();
        sorter.groupName = Executor.SYSTEM_API_GROUP_NAME;
        sorter.sourceApiXmlFile = apiXmlFile;
        sorter.outputApiXmlFile = sortedApiXmlFile;
        sorter.execute();

        assertTextFilesEqualIgnoringIndents(sortedApiXmlFile, generatedApiXmlFile);
    }

    //---------------------------------------------------------------------------------------------

    private final boolean verbose;

    private final File testPath;
    private final File outputTestPath;
    private final File testPropertiesFile;
    private final File cppFile;
    private final File outputCppFile;
    private final File apidocCppFile;
    private final File apidocXmlFile;
    private final File normalizedApidocXmlFile;
    private final File outputApidocXmlFile;
    private final File vmsPath;
    private final File outputVmsPath;
    private final File apiXmlFile;
    private final File sortedApiXmlFile;
    private final File outputApiXmlFile;
    private final File outputApiJsonFile;
    private final File templateApiXmlFile;
    private final File generatedApiXmlFile;
    private final File generatedApiJsonFile;

    private int apiXmlSystemApiFunctionsCount;

    public Tests(boolean verbose, final File testPath, final File outputTestPath)
    {
        this.verbose = verbose;
        this.testPath = testPath;
        this.outputTestPath = outputTestPath;
        this.testPropertiesFile = new File(testPath + "/test.properties");
        this.vmsPath = new File(testPath + "/netoptix_vms");
        this.outputVmsPath = new File(outputTestPath + "/netoptix_vms");
        this.cppFile = new File(vmsPath + "/appserver2/src/connection_factory.cpp");
        this.outputCppFile = new File(outputVmsPath + "/appserver2/src/connection_factory.cpp");
        this.apidocCppFile = new File(testPath + "/apidoc.cpp");
        this.apidocXmlFile = new File(testPath + "/apidoc.xml");
        this.normalizedApidocXmlFile = new File(outputTestPath + "/apidoc.NORM.xml");
        this.outputApidocXmlFile = new File(outputTestPath + "/apidoc.OUT.xml");
        this.apiXmlFile = new File(testPath + "/api.xml");
        this.sortedApiXmlFile = new File(outputTestPath + "/api.SORTED.xml");
        this.outputApiXmlFile = new File(outputTestPath + "/api.xml");
        this.outputApiJsonFile = new File(outputTestPath + "/api.json");
        this.templateApiXmlFile = new File(outputTestPath, "/api.TEMPLATE.xml");
        this.generatedApiXmlFile = new File(outputTestPath, "/api.FROM_CPP.xml");
        this.generatedApiJsonFile = new File(outputTestPath + "/api.FROM_CPP.json");

        readTestProperties();

        run("ParamsBase", new Run() { public void run() throws Exception {
            testParamsBase(); } });

        run("Xml", new Run() { public void run() throws Exception {
            testXml(); } });

        run("SourceCodeEditor", new Run() { public void run() throws Exception {
            testSourceCodeEditor(); } });

        run("SourceCodeParser", new Run() { public void run() throws Exception {
            testSourceCodeParser(); } });

        run("ApiXmlToVmsCode", new Run() { public void run() throws Exception {
            testApiXmlToVmsCode(); } });

        run("VmsCodeToApiXml", new Run() { public void run() throws Exception {
            testVmsCodeToApiXml(); } });

        run("OutputApiXmlVsOriginalXml", new Run() { public void run() throws Exception {
            testOutputApiXmlVsOriginal(); } });

        printFinalMessage();
    }
}
