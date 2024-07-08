// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.apidoc.*;
import com.nx.utils.*;

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

            apiFunctionCount = Integer.valueOf(properties.getProperty("apiFunctionCount"));
        }
        catch (Throwable e)
        {
            System.err.println();
            System.err.println("FATAL ERROR: Unable to read " + testPropertiesFile + ": "
                + e.getMessage());
            System.exit(2);
        }
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

    private void cleanUpDescription() throws Exception
    {
        final String description =
"    <br/>Example:\n" +
"    <pre><![CDATA[\n" +
"http://127.0.0.1:7001/api/createEvent?timestamp=2016-09-16T16:02:41Z" +
"&caption=CreditCardUsed&metadata={\"cameraRefs\":[\"3A4AD4EA-9269-4B1F-A7AA" +
"-2CEC537D0248\",\"3A4AD4EA-9269-4B1F-A7AA-2CEC537D0240\"]}\n" +
"]]></pre>\n" +
"    This example triggers a generic event informing the system that a\n";
        final String cleanedDescription =
"<br/>Example:\n" +
"    <pre>\n" +
"http://127.0.0.1:7001/api/createEvent?timestamp=2016-09-16T16:02:41Z" +
"&caption=CreditCardUsed&metadata={\"cameraRefs\":[\"3A4AD4EA-9269-4B1F-A7AA" +
"-2CEC537D0248\",\"3A4AD4EA-9269-4B1F-A7AA-2CEC537D0240\"]}\n" +
"</pre>\n" +
"    This example triggers a generic event informing the system that a";
        assertEquals(cleanedDescription, Utils.cleanUpDescription(description));
        assertEquals("<pre>ab</pre>",
            Utils.cleanUpDescription("<pre><![CDATA[a]]><![CDATA[b]]></pre>"));
        final String test1 = "<pre><![CDATA[a]]><![CDATA[b</pre>";
        try
        {
            Utils.cleanUpDescription(test1);
        }
        catch (Exception e)
        {
            assertEquals(e.getMessage(),
                "Unterminated CDATA section in description:\n```\n" + test1 + "\n```\n");
        }
        final String test2 = "<pre><![CDATA[a]]></pre><![CDATA[b]]>";
        try
        {
            Utils.cleanUpDescription(test2);
        }
        catch (Exception e)
        {
            assertEquals(e.getMessage(),
                "Found CDATA not inside <pre></pre> element in description:\n```\n"
                    + test2 + "\n```\n");
        }
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
        Utils.writeStringListToFile(testFile, testFileText);
        testParams.parse(testFile, Collections.<String>emptyList(), /*verbose*/ false);

        assertEquals(stringValue, testParams.stringParam());
    }

    private void testApiVersions() throws Exception
    {
        final ArrayList<ApiVersion> apiVersions = new ArrayList<>();
        apiVersions.add(new ApiVersion("/jsonrpc/v3"));
        apiVersions.add(new ApiVersion("/rest/v3"));

        final String[] paths = {
            "/old/api/path",
            "/jsonrpc/v2",
            "/rest/v2/path",
            "/rest/v3/path",
            "/rest/v4/path",

            "/jsonrpc/v{2-3}",
            "/rest/v{1-3}/path",
            "/rest/v{1-2}/path",
            "/rest/v{2-3}/path",
            "/rest/v{3-4}/path",
            "/rest/v{4-5}/path",
            "/rest/v{3-5}/path",

            "/jsonrpc/v{2-}",
            "/rest/v{1-}/path",
            "/rest/v{2-}/path",
            "/rest/v{3-}/path",
            "/rest/v{4-}/path",
            "/rest/v{5-}/path"};

        final String[] expectedPaths = {
            "/old/api/path",
            "/jsonrpc/v2",
            "/rest/v2/path",
            "/rest/v3/path",
            "/rest/v4/path",

            "/jsonrpc/v3",
            "/rest/v3/path",
            "/rest/v2/path",
            "/rest/v3/path",
            "/rest/v3/path",
            "/rest/v4/path",
            "/rest/v3/path",

            "/jsonrpc/v3",
            "/rest/v3/path",
            "/rest/v3/path",
            "/rest/v3/path",
            "/rest/v4/path",
            "/rest/v5/path"};
        for (int i = 0; i < paths.length; ++i)
        {
            String result = ApiVersion.applyExactOrNearestVersionToRange(paths[i], apiVersions);
            if (!expectedPaths[i].equals(result))
            {
                throw new RuntimeException("expectedPaths[" + i + "] " + expectedPaths[i] +
                    " is not equal to result " + result);
            }
        }

        final String[] invalidPaths = {"/rest/v{3-1}/path"};
        final String[] pathErrors = {
            "/rest/v{3-1} is invalid: first version 3 is greater than last version 1."};
        for (int i = 0; i < invalidPaths.length; ++i)
        {
            boolean isThrown = false;
            try
            {
                ApiVersion.applyExactOrNearestVersionToRange(invalidPaths[i], apiVersions);
            }
            catch (Exception e)
            {
                isThrown = true;
                if (!pathErrors[i].equals(e.getMessage()))
                {
                    throw new RuntimeException("pathErrors[" + i + "] \"" + pathErrors[i] +
                        "\" is not equal to message \"" + e.getMessage() + '"');
                }
            }
            finally
            {
                if (!isThrown)
                {
                    throw new RuntimeException("pathErrors[" + i + "] \"" + pathErrors[i] +
                        "\" is not thrown");
                }
            }
        }

        final String[] requiredPaths = {
            "/rest/v3/path",
            "/old/api/path"};
        for (int i = 0; i < requiredPaths.length; ++i)
        {
            if (ApiVersion.shouldPathBeIgnored(requiredPaths[i], apiVersions))
            {
                throw new RuntimeException("requiredPaths[" + i + "] " + requiredPaths[i] +
                    " should not be ignored");
            }
        }

        final String[] pathsToBeIgnored = {
            "/rest/v2/path",
            "/rest/v4/path"};
        for (int i = 0; i < pathsToBeIgnored.length; ++i)
        {
            if (!ApiVersion.shouldPathBeIgnored(pathsToBeIgnored[i], apiVersions))
            {
                throw new RuntimeException("pathsToBeIgnored[" + i + "] " + pathsToBeIgnored[i] +
                    " should be ignored");
            }
        }

        final String textFormat =
            "%s at the start of the first line, `%s` in the middle of line\n" +
            "%s at the start of the second line, and at the line end %s\n";
        final String[] textPaths = {
            "/rest/v3",
            "/rest/v{2-3}",
            "/rest/v{3-4}",
            "/rest/v{2-}",
            "/rest/v{3-}",
            "/jsonrpc/v3",
            "/jsonrpc/v{2-3}",
            "/jsonrpc/v{3-4}",
            "/jsonrpc/v{2-}",
            "/jsonrpc/v{3-}"};
        final String[] expectedTextPaths = {
            "/rest/v3",
            "/rest/v3",
            "/rest/v3",
            "/rest/v3",
            "/rest/v3",
            "/jsonrpc/v3",
            "/jsonrpc/v3",
            "/jsonrpc/v3",
            "/jsonrpc/v3",
            "/jsonrpc/v3"};
        for (int i = 0; i < textPaths.length; ++i)
        {
            final String expectedText = String.format(
                textFormat,
                expectedTextPaths[i],
                expectedTextPaths[i],
                expectedTextPaths[textPaths.length - i - 1],
                expectedTextPaths[textPaths.length - i - 1]);
            final String text = ApiVersion.applyExactVersion(
                String.format(
                    textFormat,
                    textPaths[i],
                    textPaths[i],
                    textPaths[textPaths.length - i - 1],
                    textPaths[textPaths.length - i - 1]),
                apiVersions);
            if (!expectedText.equals(text))
                throw new RuntimeException("\nexpectedText:\n" + expectedText + "\ntext:\n" + text);
        }

        final String[] invalidPathTexts = {
            "/rest/v{3-1}/path",
            "/rest/v2",
            "/rest/v4",
            "/rest/v{1-2}/path",
            "/rest/v{4-5}/path",
            "/rest/v{4-}/path"};
        final String[] textPathErrors = {
            "/rest/v{3-1} is invalid: first version 3 is greater than last version 1.",
            "/rest/v2 is invalid: only /rest/v3 is allowed.",
            "/rest/v4 is invalid: only /rest/v3 is allowed.",
            "/rest/v{1-2} is invalid: last version 2 is less than /rest/v3.",
            "/rest/v{4-5} is invalid: first version 4 is greater than /rest/v3.",
            "/rest/v{4-} is invalid: first version 4 is greater than /rest/v3.",
        };
        for (int i = 0; i < invalidPathTexts.length; ++i)
        {
            boolean isThrown = false;
            try
            {
                ApiVersion.applyExactVersion(invalidPathTexts[i], apiVersions);
            }
            catch (Exception e)
            {
                isThrown = true;
                if (!textPathErrors[i].equals(e.getMessage()))
                {
                    throw new RuntimeException("textPathErrors[" + i + "] \"" + textPathErrors[i] +
                        "\" is not equal to message \"" + e.getMessage() + '"');
                }
            }
            finally
            {
                if (!isThrown)
                {
                    throw new RuntimeException("textPathErrors[" + i + "] \"" + textPathErrors[i] +
                        "\" is not thrown");
                }
            }
        }
    }

    private void testApidocSerialization()
        throws Exception
    {
        final File outputExpectedApiJsonFile = new File(outputTestPath, "expected_api.json");

        final Apidoc apidoc = JsonSerializer.fromJsonString(Apidoc.class,
            Utils.readAsString(expectedApiJsonFile));

        final String json = JsonSerializer.toJsonString(apidoc);
        Utils.writeStringToFile(outputExpectedApiJsonFile, json);

        assertFileContentsEqual(expectedApiJsonFile, outputExpectedApiJsonFile);
    }

    private void testSourceCodeParserTemplate()
        throws Exception
    {
        final File templateFunctionsCppFile = new File(
            sourceCodeParserTestPath, "template_functions.cpp");
        final File expectedTemplateFunctionsJsonFile = new File(
            sourceCodeParserTestPath, "expected_template_functions.json");
        final File outputApidocJsonFile = new File(
            sourceCodeParserOutputTestPath, "template_functions.json");

        final Apidoc apidoc = JsonSerializer.fromJsonString(Apidoc.class,
            Utils.readAsString(sourceCodeParserApiTemplateJsonFile));

        TypeManager typeManager = new TypeManager(/*verbose*/ true);
        List<File> files = new ArrayList<File>();
        files.add(templateFunctionsCppFile);
        typeManager.processFiles(files, /*invalidChronoFieldSuffixIsError*/ false);

        System.out.println("test: parsing apidoc in \"template\" functions C++");
        System.out.println("    Sample: " + expectedTemplateFunctionsJsonFile);
        System.out.println("    Input: " + templateFunctionsCppFile);

        final SourceCode reader = new SourceCode(templateFunctionsCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount = sourceCodeParser.parseApidocComments(
            apidoc,
            new TemplateRegistrationMatcher(),
            typeManager,
            /*requiredFunctionCaptionLenLimit*/ -1,
            /*requiredGroupNameLenLimit*/ -1,
            /*responseChronoAsString*/ true,
            /*isTransactionBus*/ false);
        System.out.println("    API functions processed: " + processedFunctionsCount);

        Utils.writeStringToFile(outputApidocJsonFile, JsonSerializer.toJsonString(apidoc));
        System.out.println("    Output: " + outputApidocJsonFile);

        assertFileContentsEqual(outputApidocJsonFile, expectedTemplateFunctionsJsonFile);
    }

    private void testSourceCodeParserHandler()
        throws Exception
    {
        final File handlerFunctionsCppFile = new File(
            sourceCodeParserTestPath, "handler_functions.cpp");
        final File expectedHandlerFunctionsJsonFile = new File(
            sourceCodeParserTestPath, "expected_handler_functions.json");
        final File outputApidocJsonFile = new File(
            sourceCodeParserOutputTestPath, "handler_functions.json");

        final Apidoc apidoc = JsonSerializer.fromJsonString(Apidoc.class,
            Utils.readAsString(sourceCodeParserApiTemplateJsonFile));

        TypeManager typeManager = new TypeManager(/*verbose*/ true);
        List<File> files = new ArrayList<File>();
        files.add(handlerFunctionsCppFile);
        typeManager.processFiles(files, /*invalidChronoFieldSuffixIsError*/ false);

        System.out.println("test: parsing apidoc in \"handler\" functions C++");
        System.out.println("    Sample: " + expectedHandlerFunctionsJsonFile);
        System.out.println("    Input: " + handlerFunctionsCppFile);
        final SourceCode reader = new SourceCode(handlerFunctionsCppFile);
        final SourceCodeParser sourceCodeParser = new SourceCodeParser(verbose, reader);
        final int processedFunctionsCount = sourceCodeParser.parseApidocComments(
            apidoc,
            new HandlerRegistrationMatcher(),
            typeManager,
            /*requiredFunctionCaptionLenLimit*/ -1,
            /*requiredGroupNameLenLimit*/ -1,
            /*responseChronoAsString*/ true,
            /*isTransactionBus*/ false);
        System.out.println("    API functions processed: " + processedFunctionsCount);

        Utils.writeStringToFile(outputApidocJsonFile, JsonSerializer.toJsonString(apidoc));
        System.out.println("    Output: " + outputApidocJsonFile);

        assertFileContentsEqual(outputApidocJsonFile, expectedHandlerFunctionsJsonFile);
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

        final EnumParser enumParser = new EnumParser(reader, /*verbose*/ true, /*line*/ 1);
        final Map<String, EnumParser.EnumInfo> enums = enumParser.parseEnums();
        final FlagParser flagParser = new FlagParser(reader, /*verbose*/ true, /*line*/ 1);
        final Map<String, FlagParser.FlagInfo> flags = flagParser.parseFlags();
        final StructParser structParser =
            new StructParser(reader, /*verbose*/ true, /*invalidChronoFieldSuffixIsError*/ false);
        final Map<String, StructParser.StructInfo> structs = structParser.parseStructs(enums, flags);

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

        // This final separator is needed to avoid the double newline added by the code above to
        // appear at the end of the file.
        description += "-----------------------------------------------------------------------\n";

        Utils.writeStringToFile(outputStructDescriptionFile, description);

        assertFileContentsEqual(expectedStructDescriptionFile, outputStructDescriptionFile);
    }

    private void testVmsCodeToJsonExecutor()
        throws Exception
    {
        final VmsCodeToJsonExecutor executor = new VmsCodeToJsonExecutor();
        executor.verbose = verbose;
        executor.vmsPath = vmsPath;
        executor.openApiTemplateJsonFile = new File(testPath, "api_template.json");
        executor.outputOpenApiJsonFile = new File(outputTestPath, "openapi.FROM_CPP.json");
        executor.params = params;

        final int processedFunctionsCount = executor.execute();
        if (apiFunctionCount != processedFunctionsCount)
        {
            throw new RuntimeException("Expected to process " + apiFunctionCount
                + " API functions but processed " + processedFunctionsCount);
        }

        assertFileContentsEqual(expectedOpenApiJsonFile, executor.outputOpenApiJsonFile);
    }

    private void checkException(
        final VmsCodeToJsonExecutor executor, final String expectedMessage) throws Exception
    {
        String actualMessage = "";
        boolean testFailed = false;
        try
        {
            executor.execute();
            testFailed = true;
        }
        catch (Exception e)
        {
            actualMessage = e.getMessage();
            if (!actualMessage.endsWith(expectedMessage))
                testFailed = true;
        }
        if (testFailed)
        {
            throw new Exception("Expected exception thrown with message: `" + expectedMessage
                + "`, actual message is `" + actualMessage + "`.");
        }
    }

    private void notFound() throws Exception
    {
        final VmsCodeToJsonExecutor executor = new VmsCodeToJsonExecutor();
        executor.verbose = verbose;
        executor.vmsPath = new File(vmsPath, "../notfound");
        executor.params = new Params();

        final File path = new File(testPath, "notfound");
        executor.params.parsePropertiesFile(new File(path, "field.properties"));
        checkException(
            executor, "GET /rest/test: unknown type `NotFound` of parameter \"field\".");
        executor.params.parsePropertiesFile(new File(path, "parent.properties"));
        checkException(executor, "Base structure `NotFound` of `NotFoundParent` not found.");
        executor.params.parsePropertiesFile(new File(path, "struct.properties"));
        checkException(executor, "GET /rest/test: unknown type `NotFound`.");

        executor.params.parsePropertiesFile(new File(path, "overridden.properties"));
        executor.outputOpenApiJsonFile = new File(outputTestPath, "notfound_overridden.json");
        executor.execute();
        assertFileContentsEqual(new File(path, "overridden.json"), executor.outputOpenApiJsonFile);
    }

    private void errors() throws Exception
    {
        final VmsCodeToJsonExecutor executor = new VmsCodeToJsonExecutor();
        executor.verbose = verbose;
        executor.vmsPath = new File(vmsPath, "../errors");
        executor.params = new Params();

        final File path = new File(testPath, "errors");
        executor.params.parsePropertiesFile(new File(path, "struct_description.properties"));
        checkException(executor,
            "unexpected text \"Invalid description\" after declaration of type `SomeStruct`");
    }

    //---------------------------------------------------------------------------------------------

    private final boolean verbose;
    private final Params params;
    private final File testPath;
    private final File sourceCodeParserTestPath;
    private final File sourceCodeParserOutputTestPath;
    private final File sourceCodeParserApiTemplateJsonFile;
    private final File outputTestPath;
    private final File testPropertiesFile;
    private final File vmsPath;
    private final File expectedApiJsonFile;
    private final File expectedOpenApiJsonFile;

    private int apiFunctionCount;

    public Tests(boolean verbose, Params params, final File testPath, final File outputTestPath)
    {
        this.verbose = verbose;
        this.params = params;
        this.testPath = testPath;
        this.outputTestPath = outputTestPath;
        outputTestPath.mkdir();
        this.sourceCodeParserTestPath = new File(testPath, "source_code_parser");
        this.sourceCodeParserApiTemplateJsonFile = new File(
            sourceCodeParserTestPath, "api_template.json");
        this.sourceCodeParserOutputTestPath = new File(outputTestPath, "source_code_parser");
        this.testPropertiesFile = new File(testPath, "test.properties");
        this.vmsPath = new File(testPath, "nx_vms");
        this.expectedApiJsonFile = new File(testPath, "expected_api.json");
        this.expectedOpenApiJsonFile = new File(testPath, "expected_openapi.json");
        sourceCodeParserOutputTestPath.mkdirs();
        sourceCodeParserOutputTestPath.mkdir();

        readTestProperties();

        run("CleanUpDescription", new Run() { public void run() throws Exception {
            cleanUpDescription(); } });

        run("ParamsBase", new Run() { public void run() throws Exception {
            testParamsBase(); } });

        run("ApiVersions", new Run() { public void run() throws Exception {
            testApiVersions(); } });

        run("ApidocSerialization", new Run() { public void run() throws Exception {
            testApidocSerialization(); } });

        run("TypeParsers", new Run() { public void run() throws Exception {
            testTypeParsers(); } });

        run("SourceCodeParserTemplate", new Run() { public void run() throws Exception {
            testSourceCodeParserTemplate(); } });

        run("SourceCodeParserHandler", new Run() { public void run() throws Exception {
            testSourceCodeParserHandler(); } });

        run("VmsCodeToJsonExecutor", new Run() { public void run() throws Exception {
            testVmsCodeToJsonExecutor(); } });

        run("NotFound", new Run() { public void run() throws Exception {
            notFound(); } });

        run("Errors", new Run() { public void run() throws Exception {
            errors(); } });

        printFinalMessage();
    }
}
