package com.nx.apidoctool;

import com.nx.util.SimpleArgsParser;

public class Main
{
    public static void main(String[] args)
    {
        try
        {
            SimpleArgsParser arg = new SimpleArgsParser(args)
            {
                protected void showHelp()
                {
                    System.out.println(
"This tool allows to parse/generate Apidoc comments in C++ code and api.xml.\n" +
"\n" +
"Arguments:\n" +
"\n" +
"test -test-path <test-folder>\n" +
"    Perform internal tests. The folder should contain the following files:\n" +
"        api.xml\n" +
"            Complete Apidoc documentation.\n" +
"        netoptix_vms/appserver2/src/connection_factory.cpp\n" +
"            Source code with no Apidoc comments.\n" +
"\n" +
"sort-xml -group-name <name> -source-xml <file> -output-xml <file>\n" +
"    Sort the group by function name.\n" +
"\n" +
"xml-to-code -vms-path <netoptix_vms> -source-xml <file> -output-xml <file>\n" +
"    Insert Apidoc comments into the code, generated from Apidoc XML.\n" +
"    Generated source code files are given \"" + Executor.OUTPUT_FILE_EXTRA_SUFFIX + "\" suffix.\n" +
"    -output-xml is a copy of -source-xml with processed functions removed.\n" +
"\n" +
"code-to-xml -vms-path <netoptix_vms> -template-xml <file> -output-xml <file> [-output-json <file>]\n" +
"    Parse Apidoc comments in the code, and generate Apidoc XML, taking the\n" +
"    functions not mentioned in the code from -template-xml.\n" +
"    If requested, a JSON file is generated with similar contents as the XML.\n" +
"\n" +
"print-deps\n" +
"    Print paths to all C++ source code files to be accessed, relative to vms-path.\n" +
    "");
                }
            };

            if ("test".equals(arg.action()))
            {
                new Tests(arg.isVerbose(), arg.getFile("-test-path"));
            }
            else if ("sort-xml".equals(arg.action()))
            {
                final XmlSorter sorter = new XmlSorter();
                sorter.groupName = arg.get("-group-name");
                sorter.sourceApiXmlFile = arg.getFile("-source-xml");
                sorter.outputApiXmlFile = arg.getFile("-output-xml");
                sorter.execute();
            }
            else if ("xml-to-code".equals(arg.action()))
            {
                final ApiXmlToVmsCodeExecutor exec = new ApiXmlToVmsCodeExecutor();
                exec.verbose = arg.isVerbose();
                exec.vmsPath = arg.getFile("-vms-path");
                exec.sourceApiXmlFile = arg.getFile("-source-xml");
                exec.outputApiXmlFile = arg.getFile("-output-xml");
                exec.execute();
            }
            else if ("code-to-xml".equals(arg.action()))
            {
                final VmsCodeToApiXmlExecutor exec = new VmsCodeToApiXmlExecutor();
                exec.verbose = arg.isVerbose();
                exec.vmsPath = arg.getFile("-vms-path");
                exec.templateApiXmlFile = arg.getFile("-template-xml");
                exec.outputApiXmlFile = arg.getFile("-output-xml");
                exec.outputApiJsonFile = arg.getFileOptional("-output-json");
                exec.execute();
            }
            else if ("print-deps".equals(arg.action()))
            {
                Executor.printDeps();
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
