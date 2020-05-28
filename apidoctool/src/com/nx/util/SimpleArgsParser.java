package com.nx.util;

import java.io.File;
import java.net.URISyntaxException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Map-based parser for command line of the following format:
 * <code>
 *     [-verbose] <action> { <-key> "<value>" }
 * </code>
 * Keys start with "-". Key-values and action can appear in any order. On
 * error, an appropriate message is printed and System.exit(1) is performed.
 */
public abstract class SimpleArgsParser
{
    private static final String jarName = deduceJarName();

    public SimpleArgsParser(String[] args, String version, String description)
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

        if ("-invalidChronoFieldSuffixIsError".equals(args[i]))
        {
            invalidChronoFieldSuffixIsError = true;
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
                    if (map.put(arg, args[i]) != null)
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
     * Print help text to System.out, starting with the example of specific command-line arguments.
     * Description, help for generic arguments implemented by this class, and command line example
     * up to generic arguments are all printed before.
     */
    protected abstract void printUsageHelp();

    public final boolean isVerbose()
    {
        return verbose;
    }

    public final boolean invalidChronoFieldSuffixIsError()
    {
        return invalidChronoFieldSuffixIsError;
    }

    /**
     * Report an error if there was no action.
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
     * Report an error if there was no such key.
     */
    public final String getString(String key)
    {
        final String value = map.get(key);

        if (value == null)
            error("Missing \"" + key + "\".");

        return value;
    }

    public final List<String> getValuelessArgs()
    {
        return valuelessArgs;
    }

    /**
     * Report an error if there was no such key.
     */
    public final File getFile(String key)
    {
        return new File(getString(key));
    }

    /**
     * @return null If there was no such key.
     */
    public final File getOptionalFile(String key)
    {
        final String value = map.get(key);

        if (value == null)
            return null;

        return new File(value);
    }

    //--------------------------------------------------------------------------

    private void error(String message)
    {
        System.err.print("ERROR in arguments: ");
        System.err.println(message);
        System.err.println("");
        System.err.println("Run with \"-h\" for help.");

        System.exit(1);
    }

    private static String deduceJarName()
    {
        final String jarUri;
        try
        {
            jarUri = SimpleArgsParser.class.getProtectionDomain().getCodeSource().getLocation()
                .toURI().toString();
        }
        catch (URISyntaxException e)
        {
            throw new RuntimeException("Unable to get .jar file name: " + e.getMessage(), e);
        }

        return jarUri.substring(jarUri.lastIndexOf('/') + 1);
    }

    private void printHelp(String version, String description)
    {
        final String command = "java -jar " + jarName;

        System.out.println(jarName + " version " + version);
        System.out.println();
        System.out.println(description);
        System.out.println();
        System.out.print(
            "Show help:\n" +
            " " + command + " [-h|-help|--help]\n" +
            "\n" +
            "Show version:\n" +
            " " + command + " -version|--version\n" +
            "\n" +
            "Usage:\n" +
            " " + command + " [-verbose] [-invalidChronoFieldSuffixIsError]");
        printUsageHelp();
    }

    //--------------------------------------------------------------------------

    private boolean verbose = false;
    private boolean invalidChronoFieldSuffixIsError = false;
    private String action;
    private Map<String, String> map = new HashMap<String, String>();
    private List<String> valuelessArgs = new ArrayList<String>();
}
