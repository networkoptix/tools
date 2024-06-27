// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.utils.ArgParser;

import java.io.InputStream;
import java.util.Properties;

public class Main
{
    private static final String VERSION = "3.0";

    private static final String DESCRIPTION =
        "Parses Apidoc comments in C++ code and generates JSON files with the API documentation.";

    private static final String HELP =
"Actions (the first term is the <action> argument):\n" +
"\n" +
" test -test-path <test-folder> -output-test-path <output-folder>\n" +
"     Run unit tests. Generated files are saved to -output-test-path folder (will be created).\n" +
"     The -test-path folder should contain the following files:\n" +
"         api.json\n" +
"             Complete Apidoc documentation.\n" +
"         nx_vms/appserver2/src/connection_factory.cpp\n" +
"             Source code with /ec2 handler registration calls, with no Apidoc comments.\n" +
"\n" +
" code-to-json -vms-path <nx_vms> [-openapi-template-json <file>] -output-openapi-json <file>\n" +
"     Parse Apidoc comments in the code, and generate OpenAPI JSON, using the\n" +
"     -openapi-template-json if specified.\n" +
"\n" +
" print-deps -vms-path <nx_vms>\n" +
"    Print paths to all C++ source code files to be read by code-to-json, relative to vms-path.\n" +
"\n" +
"Common <key> arguments:\n" +
"\n" +
" To find necessary places in C++ code, this tool uses a number of parameters like C++ file\n" +
" names, regex patterns of C++ lines of interest, etc.\n" +
"\n" +
" To override these values, specify a number of arguments in the form:\n" +
"\n" +
"  -D<param>=<value>...\n" +
"\n" +
" and/or put the values into a .properties file with name=value lines, and specify its name:\n" +
"\n" +
"  -config <filename.properties>\n";

    private static ArgParser createArgParser(String[] args, Params params)
        throws Exception
    {
        final Properties properties = new Properties();
        final InputStream propertiesInput =
            Main.class.getClassLoader().getResourceAsStream("version.properties");
        if (propertiesInput != null)
            properties.load(propertiesInput);

        return new ArgParser(args,
            VERSION + "-" + properties.getProperty("gitSha", "unknown").replace("-dirty", "+"),
            DESCRIPTION)
        {
            protected void printUsageHelp()
            {
                System.out.print(HELP);
                System.out.println(
                    "\nHere is the list of supported params and their default values:\n");
                params.printHelp(System.out, /*linePrefix*/ " ");
            }
        };
    }

    private static void run(String[] args)
        throws Exception
    {
        final Params params = new Params();
        final ArgParser argParser = createArgParser(args, params);

        params.parse(
            argParser.optionalFile("-config"),
            argParser.valuelessArgs(),
            argParser.isVerbose());

        if ("test".equals(argParser.action()))
        {
            new Tests(argParser.isVerbose(), params,
                argParser.file("-test-path"), argParser.file("-output-test-path"));
        }
        else if ("code-to-json".equals(argParser.action())
            || "code-to-xml".equals(argParser.action())) //< Deprecated arg name.
        {
            final VmsCodeToJsonExecutor executor = new VmsCodeToJsonExecutor();
            executor.verbose = argParser.isVerbose();
            executor.vmsPath = argParser.file("-vms-path");
            executor.outputOpenApiJsonFile = argParser.file("-output-openapi-json");
            executor.openApiTemplateJsonFile = argParser.optionalFile("-openapi-template-json");
            executor.params = params;
            executor.execute();
        }
        else if ("print-deps".equals(argParser.action()))
        {
            final PrintDepsExecutor executor = new PrintDepsExecutor();
            executor.vmsPath = argParser.optionalFile("-vms-path");
            executor.params = params;
            executor.execute();
        }
        else
        {
            argParser.reportUnsupportedAction();
        }
    }

    public static void main(String[] args)
    {
        ClassLoader.getSystemClassLoader().setDefaultAssertionStatus(true);
        try
        {
            run(args);
        }
        catch (Throwable e)
        {
            if (e instanceof Exception && !(e instanceof RuntimeException))
            {
                // Application-level exception.
                System.err.println("ERROR: " + e.getMessage());
                System.exit(1);
            }
            else
            {
                e.printStackTrace();
                System.exit(2);
            }
        }
    }
}
