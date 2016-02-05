package com.nx.apidoctool;

import java.io.File;

public class Main
{
    private static final String CONNECTION_FACTORY_CPP_FILE =
        "/appserver2/src/connection_factory.cpp";

    private static void showHelp()
    {
        System.out.println(
"This tool allows to parse/generate Apidoc comments in C++ code and api.xml.\n" +
"Arguments:\n" +
"-test <path/to/test/folder>\n" +
"    Perform unit tests. The folder should contain the following files:\n" +
"        \"api.xml\" - with complete Apidoc documentation.\n" +
"        \"connection_factory.cpp\" - with no Apidoc comments.\n" +
"-sort-xml <groupName> <input_api.xml> <output_api.xml>\n" +
"    Sort the group by function name.\n" +
"-xml-to-code <path/to/netoptix_vms> <source-api.xml> <target-api.xml> <output.cpp>\n" +
"    Insert Apidoc comments into the code, generated from Apidoc XML.\n" +
"    <target-api.xml> is a copy of <source-api.xml> with processed functions removed.\n" +
"-code-to-xml <path/to/netoptix_vms> <template.xml> <output.xml>\n" +
"    Parse Apidoc comments in the code, and generate Apidoc XML, taking the\n" +
"    functions not mentioned in the code from <template.xml>.\n" +
            "");
    }

    public static void main(String[] args)
    {
        try
        {
            if (args.length == 0 || (args[0].matches("-h|-help|--help")))
            {
                showHelp();
                System.exit(0);
            }
            else if (checkArgs(args, "-test", 2))
            {
                // <path/to/test/folder>
                new Tests(new File(args[1]));
            }
            else if (checkArgs(args, "-sort-xml", 4))
            {
                // <groupName> <input_api.xml> <output_api.xml>
                MainHandler.sortXml(args[1], new File(args[2]), new File(args[3]));
            }
            else if (checkArgs(args, "-xml-to-code", 5))
            {
                // <path/to/netoptix_vms> <source-api.xml> <target-api.xml> <output.cpp>
                xmlToCode(new File(args[1]), new File(args[2]), new File(args[3]), new File(args[4]));
            }
            else if (checkArgs(args, "-code-to-xml", 4))
            {
                // <path/to/netoptix_vms> <template.xml> <output.xml>
                codeToXml(new File(args[1]), new File(args[2]), new File(args[3]));
            }
            else
            {
                System.err.println("ERROR: Invalid args. Run with -h for help.");
                System.exit(1);
            }
        }
        catch (Throwable e)
        {
            e.printStackTrace();
            System.exit(2);
        }
    }

    private static boolean checkArgs(String[] args, String arg, int count)
    {
        assert args.length > 0;

        if (!arg.equals(args[0]))
            return false;

        if (args.length != count)
        {
            System.err.println(
                "ERROR: " + count + " args expected, " + args.length +
                " found:");
            for (String existingArg: args)
                System.out.println(existingArg);
            System.out.println("Run with -h for help.");
            System.exit(1);
        }

        return true;
    }

    private static void xmlToCode(
        File vmsPath, File sourceApiXmlFile, File outputApiXmlFile,
        File outputConnectionFactoryCppFile)
        throws Exception
    {
        final File connectionFactoryCppFile = new File(
            vmsPath + CONNECTION_FACTORY_CPP_FILE);

        MainHandler.xmlToCode(sourceApiXmlFile, outputApiXmlFile,
            connectionFactoryCppFile, outputConnectionFactoryCppFile);
    }

    private static void codeToXml(
        File vmsPath, File templateApiXmlFile, File outputApiXmlFile)
        throws Exception
    {
        final File connectionFactoryCppFile = new File(vmsPath +
            CONNECTION_FACTORY_CPP_FILE);

        // NOTE: This code can be easily rewritten to avoid converting untouched
        // XML groups to Apidoc and back.

        MainHandler.codeToXml(
            connectionFactoryCppFile, templateApiXmlFile, outputApiXmlFile);
    }
}
