package com.nx.apidoctool;

import com.nx.apidoc.*;
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

            apiXmlFunctionsCount = Integer.valueOf(properties.getProperty("apiXmlFunctionsCount"));
        }
        catch (Throwable e)
        {
            System.err.println();
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
        final TestParams testParams = new TestParams();
        assertEquals("default value", testParams.stringParam());
        testParams.printHelp(System.out, "    ");

        testParamsBaseInvalidArg(testParams, "-Dunknown=value");
        testParamsBaseInvalidArg(testParams, "-D=missingName");
        testParamsBaseInvalidArg(testParams, "-DstringParam");
        testParamsBaseInvalidArg(testParams, "noMinusD");

        final String stringValue = "Value with 2 spaces,\\backslash,\ttab,\nnewline";

        testParams.parse(
            /*optionalFile*/ null,
            Arrays.asList("-DstringParam=" + stringValue),
            /*verbose*/ true);
        assertEquals(stringValue, testParams.stringParam());

        testParams.stringParam.setLength(0);

        final List<String> testFileText = Arrays.asList(
            "stringParam=Value with 2 spaces,\\\\backslash,\\ttab,\\nnewline",
            "# End of file");

        final File testFile = new File(outputTestPath, "params.properties");
        Utils.writeStringListToFile(testFile, testFileText, /*lineBreak*/ "\n");
        testParams.parse(testFile, Collections.<String>emptyList(), /*verbose*/ false);

        assertEquals(stringValue, testParams.stringParam());
    }

    private void testApidocSerialization()
        throws Exception
    {
        final File outputExpectedApiXmlFile = new File(outputTestPath, "expected_api.xml");
        final File outputExpectedApiJsonFile = new File(outputTestPath, "expected_api.json");

        apiXmlToXml(expectedApiXmlFile, outputExpectedApiXmlFile, outputExpectedApiJsonFile);

        assertFileContentsEqual(expectedApiXmlFile, outputExpectedApiXmlFile);
        assertJsonEqualsXml(outputExpectedApiJsonFile, outputExpectedApiXmlFile);
    }

    private void testSourceCodeEditor()
        throws Exception
    {
        final File outputCppFile = new File(outputVmsPath, params.templateRegistrationCpp());
        final File cppFile = new File(vmsPath, params.templateRegistrationCpp());

        final SourceCodeEditor sourceCodeEditor = new SourceCodeEditor(cppFile);
        sourceCodeEditor.saveToFile(outputCppFile);

        assertFileContentsEqual(cppFile, outputCppFile);
    }

    private void testSourceCodeParserTemplate()
        throws Exception
    {
        final File templateFunctionsCppFile = new File(
            sourceCodeParserTestPath, "template_functions.cpp");
        final File expectedTemplateFunctionsXmlFile = new File(
            sourceCodeParserTestPath, "expected_template_functions.xml");
        final File outputApidocXmlFile = new File(
            sourceCodeParserOutputTestPath, "template_functions.xml");

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
            XmlUtils.parseXmlFile(sourceCodeParserApiTemplateXmlFile));

        TypeMananger typeMananger = new TypeMananger(/*verbose*/ true);
        List<File> files = new ArrayList<File>();
        files.add(templateFunctionsCppFile);
        typeMananger.processFiles(files);

        System.out.println("test: parsing apidoc in \"template\" functions C++");
        System.out.println("    Sample: " + expectedTemplateFunctionsXmlFile);
        System.out.println("    Input: " + templateFunctionsCppFile);

        final SourceCode reader = new SourceCode(templateFunctionsCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount = sourceCodeParser.parseApidocComments(
            apidoc, new TemplateRegistrationMatcher(), typeMananger);
        System.out.println("    API functions processed: " + processedFunctionsCount);

        XmlUtils.writeXmlFile(outputApidocXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApidocXmlFile);

        assertFileContentsEqual(outputApidocXmlFile, expectedTemplateFunctionsXmlFile);
    }

    private void testSourceCodeParserHandler()
        throws Exception
    {
        final File handlerFunctionsCppFile = new File(
            sourceCodeParserTestPath, "handler_functions.cpp");
        final File expectedHandlerFunctionsXmlFile = new File(
            sourceCodeParserTestPath, "expected_handler_functions.xml");
        final File outputApidocXmlFile = new File(
            sourceCodeParserOutputTestPath, "handler_functions.xml");

        final Apidoc apidoc = XmlSerializer.fromDocument(Apidoc.class,
                XmlUtils.parseXmlFile(sourceCodeParserApiTemplateXmlFile));

        System.out.println("test: parsing apidoc in \"handler\" functions C++");
        System.out.println("    Sample: " + expectedHandlerFunctionsXmlFile);
        System.out.println("    Input: " + handlerFunctionsCppFile);
        final SourceCode reader = new SourceCode(handlerFunctionsCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount = sourceCodeParser.parseApidocComments(
                apidoc, new HandlerRegistrationMatcher(), null);
        System.out.println("    API functions processed: " + processedFunctionsCount);

        XmlUtils.writeXmlFile(outputApidocXmlFile, XmlSerializer.toDocument(apidoc));
        System.out.println("    Output: " + outputApidocXmlFile);

        assertFileContentsEqual(outputApidocXmlFile, expectedHandlerFunctionsXmlFile);
    }

    private void testTypeParsers()
        throws Exception
    {
        final File structHeaderFile = new File(
            sourceCodeParserTestPath, "structs.h");
        final File expectedStructDescriptionFile = new File(
            sourceCodeParserTestPath, "expected_structs.txt");
        final File outputStructDescriptionFile = new File(
            sourceCodeParserOutputTestPath, "structs.txt");

        System.out.println("test: parsing apidoc structs and enums in C++");
        System.out.println("    Input: " + structHeaderFile);
        System.out.println("    Output: " + outputStructDescriptionFile);
        final SourceCode reader = new SourceCode(structHeaderFile);

        final EnumParser enumParser = new EnumParser(reader, true);
        final Map<String, EnumParser.EnumInfo> enums = enumParser.parseEnums();

        List<EnumParser.EnumInfo> enumList =
            new ArrayList<EnumParser.EnumInfo>(enums.values());
        Collections.sort(enumList,
            new Comparator<EnumParser.EnumInfo>()
            {
                public int compare(EnumParser.EnumInfo e1, EnumParser.EnumInfo e2)
                {
                    return e1.name.compareTo(e2.name);
                }
            });

        String description = "";
        description += "-----------------------------------------------------------------------\n";
        description += "- Enums\n\n";
        for (EnumParser.EnumInfo enumInfo: enumList)
            description += enumInfo.toString() + "\n";

        description += "-----------------------------------------------------------------------\n";
        description += "- Structs\n\n";
        final StructParser structParser = new StructParser(reader, true);
        final Map<String, StructParser.StructInfo> structs = structParser.parseStructs();
        List<StructParser.StructInfo> structList =
            new ArrayList<StructParser.StructInfo>(structs.values());
        Collections.sort(structList,
            new Comparator<StructParser.StructInfo>()
            {
                public int compare(StructParser.StructInfo s1, StructParser.StructInfo s2)
                {
                    return s1.name.compareTo(s2.name);
                }
            });
        for (StructParser.StructInfo structInfo: structList)
            description += structInfo.toString() + "\n";

        Utils.writeStringToFile(outputStructDescriptionFile, description);

        assertFileContentsEqual(expectedStructDescriptionFile, outputStructDescriptionFile);
    }

    private void VmsCodeToApiXmlExecutor()
        throws Exception
    {
        final File apiTemplateXmlFile = new File(testPath, "api_template.xml");
        final File generatedApiXmlFile = new File(outputTestPath, "api.FROM_CPP.xml");
        final File generatedApiJsonFile = new File(outputTestPath, "api.FROM_CPP.json");

        final VmsCodeToApiXmlExecutor executor = new VmsCodeToApiXmlExecutor();
        executor.verbose = verbose;
        executor.vmsPath = vmsPath;
        executor.templateApiXmlFile = apiTemplateXmlFile;
        executor.outputApiXmlFile = generatedApiXmlFile;
        executor.optionalOutputApiJsonFile = generatedApiJsonFile;
        executor.params = params;

        final int processedFunctionsCount = executor.execute();
        if (apiXmlFunctionsCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiXmlFunctionsCount
                + " API functions but processed " + processedFunctionsCount);
        }

        assertJsonEqualsXml(generatedApiJsonFile, generatedApiXmlFile);

        assertFileContentsEqual(expectedApiXmlFile, generatedApiXmlFile);
    }

    //---------------------------------------------------------------------------------------------

    private final boolean verbose;
    private final Params params;
    private final File testPath;
    private final File sourceCodeParserTestPath;
    private final File sourceCodeParserOutputTestPath;
    private final File sourceCodeParserApiTemplateXmlFile;
    private final File outputTestPath;
    private final File testPropertiesFile;
    private final File vmsPath;
    private final File outputVmsPath;
    private final File expectedApiXmlFile;

    private int apiXmlFunctionsCount;

    public Tests(boolean verbose, Params params, final File testPath, final File outputTestPath)
    {
        this.verbose = verbose;
        this.params = params;
        this.testPath = testPath;
        this.outputTestPath = outputTestPath;
        this.sourceCodeParserTestPath = new File(testPath, "source_code_parser");
        this.sourceCodeParserApiTemplateXmlFile = new File(
            sourceCodeParserTestPath, "api_template.xml");
        this.sourceCodeParserOutputTestPath = new File(outputTestPath, "source_code_parser");
        this.testPropertiesFile = new File(testPath, "test.properties");
        this.vmsPath = new File(testPath, "nx_vms");
        this.outputVmsPath = new File(outputTestPath, "nx_vms");
        this.expectedApiXmlFile = new File(testPath, "expected_api.xml");
        sourceCodeParserOutputTestPath.mkdirs();
        sourceCodeParserOutputTestPath.mkdir();

        readTestProperties();

        run("ParamsBase", new Run() { public void run() throws Exception {
            testParamsBase(); } });

        run("ApidocSerialization", new Run() { public void run() throws Exception {
            testApidocSerialization(); } });

        run("SourceCodeEditor", new Run() { public void run() throws Exception {
            testSourceCodeEditor(); } });

        run("TypeParsers", new Run() { public void run() throws Exception {
            testTypeParsers(); } });

        run("SourceCodeParserTemplate", new Run() { public void run() throws Exception {
            testSourceCodeParserTemplate(); } });

        run("SourceCodeParserHanlder", new Run() { public void run() throws Exception {
            testSourceCodeParserHandler(); } });

        run("VmsCodeToApiXmlExecutor", new Run() { public void run() throws Exception {
            VmsCodeToApiXmlExecutor(); } });

        printFinalMessage();
    }
}
