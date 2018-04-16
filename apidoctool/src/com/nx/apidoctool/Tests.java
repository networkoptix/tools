package com.nx.apidoctool;

import com.nx.apidoc.Apidoc;
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

            apiXmlFunctionsCount = Integer.valueOf(
                properties.getProperty("apiXmlFunctionsCount"));
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

    private void testApidocSerialization()
        throws Exception
    {
        final File outputExpectedApiXmlFile = new File(outputTestPath + "/expected_api.xml");
        final File outputExpectedApiJsonFile = new File(outputTestPath + "/expected_api.json");

        apiXmlToXml(expectedApiXmlFile, outputExpectedApiXmlFile, outputExpectedApiJsonFile);

        assertFileContentsEqual(expectedApiXmlFile, outputExpectedApiXmlFile);
        assertJsonEqualsXml(outputExpectedApiJsonFile, outputExpectedApiXmlFile);
    }

    private void testSourceCodeEditor()
        throws Exception
    {
        final File outputCppFile = new File(outputTestPath + "/nx_vms/appserver2/src/connection_factory.cpp");
        final File cppFile = new File(vmsPath + "/appserver2/src/connection_factory.cpp");

        final SourceCodeEditor sourceCodeEditor = new SourceCodeEditor(cppFile);
        sourceCodeEditor.saveToFile(outputCppFile);

        assertFileContentsEqual(cppFile, outputCppFile);
    }

    private void testSourceCodeParserTemplate()
        throws Exception
    {
        final File templateFunctionsCppFile = new File(sourceCodeParserTestPath + "/template_functions.cpp");
        final File expectedTemplateFunctionsXmlFile = new File(
                sourceCodeParserTestPath + "/expected_template_functions.xml");
        final File outputApidocXmlFile = new File(sourceCodeParserOutputTestPath + "/template_functions.xml");

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
                XmlUtils.parseXmlFile(sourceCodeParserApiTemplateXmlFile));

        System.out.println("test: parsing apidoc in \"template\" type C++ and comparing it to the expected XML");
        System.out.println("    Sample: " + expectedTemplateFunctionsXmlFile);
        System.out.println("    Input: " + templateFunctionsCppFile);

        final SourceCode reader = new SourceCode(templateFunctionsCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount =
            sourceCodeParser.parseApidocComments(apidoc, new TemplateRegistrationMatcher());
        System.out.println("    API functions processed: " + processedFunctionsCount);


        XmlUtils.writeXmlFile(outputApidocXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApidocXmlFile);

        assertFileContentsEqual(outputApidocXmlFile, expectedTemplateFunctionsXmlFile);
    }

    private void testSourceCodeParserHandler()
        throws Exception
    {
        final File handlerFunctionsCppFile = new File(sourceCodeParserTestPath + "/handler_functions.cpp");
        final File expectedHandlerFunctionsXmlFile = new File(
            sourceCodeParserTestPath + "/expected_handler_functions.xml");
        final File outputApidocXmlFile = new File(sourceCodeParserOutputTestPath + "/handler_functions.xml");

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
                XmlUtils.parseXmlFile(sourceCodeParserApiTemplateXmlFile));

        System.out.println("test: parsing apidoc in \"handler\" type C++ and comparing it to the expected XML");
        System.out.println("    Sample: " + expectedHandlerFunctionsXmlFile);
        System.out.println("    Input: " + handlerFunctionsCppFile);
        final SourceCode reader = new SourceCode(handlerFunctionsCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount =
                sourceCodeParser.parseApidocComments(apidoc, new HandlerRegistrationMatcher());
        System.out.println("    API functions processed: " + processedFunctionsCount);

        XmlUtils.writeXmlFile(outputApidocXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApidocXmlFile);

        assertFileContentsEqual(outputApidocXmlFile, expectedHandlerFunctionsXmlFile);
    }

    private void VmsCodeToApiXmlExecutor()
        throws Exception
    {
        final File apiTemplateXmlFile = new File(testPath + "/api_template.xml");
        final File generatedApiXmlFile = new File(outputTestPath, "/api.FROM_CPP.xml");
        final File generatedApiJsonFile = new File(outputTestPath + "/api.FROM_CPP.json");

        final VmsCodeToApiXmlExecutor executor = new VmsCodeToApiXmlExecutor();
        executor.verbose = verbose;
        executor.vmsPath = vmsPath;
        executor.templateApiXmlFile = apiTemplateXmlFile;
        executor.outputApiXmlFile = generatedApiXmlFile;
        executor.optionalOutputApiJsonFile = generatedApiJsonFile;
        executor.params = new Params();

        final int processedFunctionsCount = executor.execute();
        if (apiXmlFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiXmlFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }

        assertJsonEqualsXml(generatedApiJsonFile, generatedApiXmlFile);

        assertTextFilesEqualIgnoringIndents(expectedApiXmlFile, generatedApiXmlFile);
    }

    //---------------------------------------------------------------------------------------------

    private final boolean verbose;

    private final File testPath;
    private final File sourceCodeParserTestPath;
    private final File sourceCodeParserOutputTestPath;
    private final File sourceCodeParserApiTemplateXmlFile;
    private final File outputTestPath;
    private final File testPropertiesFile;
    private final File vmsPath;
    private final File expectedApiXmlFile;

    private int apiXmlFunctionsCount;

    public Tests(boolean verbose, final File testPath, final File outputTestPath)
    {
        this.verbose = verbose;
        this.testPath = testPath;
        this.outputTestPath = outputTestPath;
        this.sourceCodeParserTestPath = new File(testPath + "/source_code_parser");
        this.sourceCodeParserApiTemplateXmlFile = new File(sourceCodeParserTestPath + "/api_template.xml");
        this.sourceCodeParserOutputTestPath = new File(outputTestPath + "/source_code_parser");
        this.testPropertiesFile = new File(testPath + "/test.properties");
        this.vmsPath = new File(testPath + "/nx_vms");
        this.expectedApiXmlFile = new File(testPath + "/expected_api.xml");
        sourceCodeParserOutputTestPath.mkdirs();
        sourceCodeParserOutputTestPath.mkdir();


        readTestProperties();

        run("ParamsBase", new Run() { public void run() throws Exception {
            testParamsBase(); } });

        run("ApidocSerialization", new Run() { public void run() throws Exception {
            testApidocSerialization(); } });

        run("SourceCodeEditor", new Run() { public void run() throws Exception {
            testSourceCodeEditor(); } });

        run("SourceCodeParserTemplate", new Run() { public void run() throws Exception {
            testSourceCodeParserTemplate(); } });

        run("SourceCodeParserHanlder", new Run() { public void run() throws Exception {
            testSourceCodeParserHandler
                    (); } });


        run("VmsCodeToApiXmlExecutor", new Run() { public void run() throws Exception {
            VmsCodeToApiXmlExecutor(); } });

        printFinalMessage();
    }
}
