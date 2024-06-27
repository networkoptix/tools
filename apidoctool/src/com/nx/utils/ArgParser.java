// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.utils;

import java.io.File;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Simple map-based parser for command line arguments.
 *
 * To use, inherit and implement the required protected methods.
 *
 * The supported command line formats are:
 * <code>
 *     [-h|-help|--help]
 *     -version|--version
 *     [-verbose] <action> {-<key> [<value>]}...
 * </code>
 * Keys start with "-". Key-values and <action> can appear in any order. On error, an appropriate
 * message is printed and System.exit(1) is performed.
 */
public abstract class ArgParser
{
    private static final String jarName = "apidoctool.jar";

    public ArgParser(String[] args, String version, String description)
    {
        if (args.length == 0 || (args[0].matches("-h|-help|--help")))
        {
            printHelp(version, description);
            System.exit(0);
        }

        if (args[0].matches("-version|--version"))
        {
            System.out.println(version);
            System.exit(0);
        }

        int i = 0;
        if ("-verbose".equals(args[i]))
        {
            verbose = true;
            ++i;
        }

        while (i < args.length)
        {
            final String arg = args[i];
            ++i;

            if (arg.startsWith("-"))
            {
                if (i >= args.length || args[i].startsWith("-"))
                {
                    // There is no value for this key.
                    if (valuelessArgs.contains(arg))
                        error("Valueless key \"" + arg + "\" is specified more than once.");
                    valuelessArgs.add(arg);
                }
                else
                {
                    if (keys.put(arg, args[i]) != null)
                        error("Key \"" + arg + "\" is specified more than once.");
                    ++i;
                }
            }
            else
            {
                if (action != null)
                {
                    error("<action> is specified more than once: " +
                        "\"" + action + "\" and \"" + arg + "\".");
                }
                action = arg;
            }
        }
    }

    /**
     * Prints the help text to stdout, starting with the description of the <action> values.
     * The description and the help for generic arguments implemented by this class is already
     * printed above this text.
     */
    protected abstract void printUsageHelp();

    /**
     * @return Whether -verbose or --verbose has been specified.
     */
    public final boolean isVerbose()
    {
        return verbose;
    }

    /**
     * Reports an error if there was no action.
     */
    public final String action()
    {
        if (action == null)
            error("<action> is missing.");

        return action;
    }

    public final void reportUnsupportedAction()
    {
        if (action == null)
            error("<action> is missing.");

        error("Action \"" + action + "\" is not supported.");
    }

    /**
     * Reports an error if there was no such key.
     */
    public final String value(String key)
    {
        final String value = keys.get(key);

        if (value == null)
            error("Missing \"" + key + "\".");

        return value;
    }

    public final List<String> valuelessArgs()
    {
        return valuelessArgs;
    }

    /**
     * Reports an error if there was no such key.
     */
    public final File file(String key)
    {
        return new File(value(key));
    }

    /**
     * @return Null If there was no such key.
     */
    public final File optionalFile(String key)
    {
        final String value = keys.get(key);

        if (value == null)
            return null;

        return new File(value);
    }

    //---------------------------------------------------------------------------------------------

    private void error(String message)
    {
        System.err.print("ERROR in arguments: ");
        System.err.println(message);
        System.err.println();
        System.err.println("Run with \"-h\" for help.");

        System.exit(1);
    }

    private void printHelp(String version, String description)
    {
        final String command = "java -jar " + jarName;

        System.out.println(jarName + " version " + version);
        System.out.println();
        System.out.println(description);
        System.out.println();
        System.out.println(
            "Show help:\n" +
            " " + command + " [-h|-help|--help]\n" +
            "\n" +
            "Show version:\n" +
            " " + command + " -version|--version\n" +
            "\n" +
            "Execute action:\n" +
            " " + command + " [-verbose] <action> {-<key> [<value>]}...\n");

        printUsageHelp();
    }

    //---------------------------------------------------------------------------------------------

    private boolean verbose = false;
    private String action;
    private Map<String, String> keys = new HashMap<String, String>();
    private List<String> valuelessArgs = new ArrayList<String>();
}
