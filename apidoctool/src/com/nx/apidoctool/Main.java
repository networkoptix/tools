package com.nx.apidoctool;

import com.nx.util.SimpleArgsParser;

public class Main
{
    private static final String HELP =
"This tool allows to parse/generate Apidoc comments in C++ code and api.xml.\n" +
"Usage:\n" +
" java -jar apidoctool.jar [-verbose] <command> [<params>]\n" +
"\n" +
"<command>:\n" +
"\n" +
" test -test-path <test-folder> -output-test-path <output-folder>\n" +
"     Run unit tests. Generated files are saved to -output-test-path folder (will be created).\n" +
"     The -test-path folder should contain the following files:\n" +
"         api.xml\n" +
"             Complete Apidoc documentation.\n" +
"         nx_vms/appserver2/src/connection_factory.cpp\n" +
"             Source code with /ec2 handler registration calls,with no Apidoc comments.\n" +
"\n" +
" sort-xml -group-name <name> -source-xml <file> -output-xml <file>\n" +
"     Sort the group by function name.\n" +
"\n" +
" xml-to-code -vms-path <nx_vms> [-output-vms-path <nx_vms>] -source-xml <file> -output-xml <file>\n" +
"     Insert Apidoc comments into the code, generated from Apidoc XML. Generated source code\n" +
"     files are given \"" + Executor.OUTPUT_FILE_EXTRA_SUFFIX + "\" suffix, and are saved to\n" +
"     the specified -output-vms-path location, or, if omitted, to -vms-path.\n" +
"     Generated -output-xml file is a copy of -source-xml with processed functions removed.\n" +
"\n" +
" code-to-xml -vms-path <nx_vms> -template-xml <file> -output-xml <file> [-output-json <file>]\n" +
"     Parse Apidoc comments in the code, and generate Apidoc XML, taking the functions not\n" +
"     mentioned in the code from -template-xml. If requested, a JSON file is generated with\n" +
"     similar contents as the XML.\n" +
"\n" +
" print-deps\n" +
"    Print paths to all C++ source code files to be read by code-to-xml, relative to vms-path.\n" +
"\n" +
"<params>:\n" +
"\n" +
" To find necessary places in C++ code, this tool uses a number of parameters like C++ file\n" +
" names, regex patterns of C++ lines of interest, etc. Such parameters have default values\n" +
" hard-coded in this tool, which are suitable for VMS v3.1 and older.\n" +
"\n" +
" To override these values, specify a number of arguments in the form:\n" +
"     -D<param>=<value>...\n" +
" and/or put the values into a .properties file with name=value lines, and specify its name:\n" +
"     -config <filename.properties>\n" +
"\n" +
" Here is the list of supported params and their default values:\n" +
"\n";

    public static void main(String[] args)
    {
        try
        {
            final Params params = new Params();

            final SimpleArgsParser arg = new SimpleArgsParser(args)
            {
                protected void showHelp()
                {
                    System.out.print(HELP);
                    params.printHelp(System.out, /*linePrefix*/ "    ");
                }
            };

            params.parse(arg.getOptionalFile("-config"), arg.getValuelessArgs(), arg.isVerbose());

            if ("test".equals(arg.action()))
            {
                arg.reportUnexpectedValuelessArgs();
                new Tests(
                    arg.isVerbose(), arg.getFile("-test-path"), arg.getFile("-output-test-path"));
            }
            else if ("sort-xml".equals(arg.action()))
            {
                arg.reportUnexpectedValuelessArgs();
                final XmlSorter sorter = new XmlSorter();
                sorter.groupName = arg.get("-group-name");
                sorter.sourceApiXmlFile = arg.getFile("-source-xml");
                sorter.outputApiXmlFile = arg.getFile("-output-xml");
                sorter.execute();
            }
            else if ("xml-to-code".equals(arg.action()))
            {
                final ApiXmlToVmsCodeExecutor executor = new ApiXmlToVmsCodeExecutor();
                executor.verbose = arg.isVerbose();
                executor.vmsPath = arg.getFile("-vms-path");
                executor.optionalOutputVmsPath = arg.getOptionalFile("-output-vms-path");
                executor.sourceApiXmlFile = arg.getFile("-source-xml");
                executor.outputApiXmlFile = arg.getFile("-output-xml");
                executor.params = params;
                executor.execute();
            }
            else if ("code-to-xml".equals(arg.action()))
            {
                final VmsCodeToApiXmlExecutor executor = new VmsCodeToApiXmlExecutor();
                executor.verbose = arg.isVerbose();
                executor.vmsPath = arg.getFile("-vms-path");
                executor.templateApiXmlFile = arg.getFile("-template-xml");
                executor.outputApiXmlFile = arg.getFile("-output-xml");
                executor.optionalOutputApiJsonFile = arg.getOptionalFile("-output-json");
                executor.params = params;
                executor.execute();
            }
            else if ("print-deps".equals(arg.action()))
            {
                final PrintDepsExecutor executor = new PrintDepsExecutor();
                executor.params = params;
                executor.execute();
            }
            else
            {
                arg.reportUnsupportedAction();
            }
        }
        catch (Throwable e)
        {
            e.printStackTrace();
            System.exit(2);
        }
    }
}
