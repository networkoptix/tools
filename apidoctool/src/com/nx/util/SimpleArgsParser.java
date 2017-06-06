package com.nx.util;

import java.io.File;
import java.util.HashMap;
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
    public SimpleArgsParser(String[] args)
    {
        if (args.length == 0 || (args[0].matches("-h|-help|--help")))
        {
            showHelp();
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
                if (i >= args.length)
                    error("Missing value for \"" + arg + "\".");

                if (map.put(arg, args[i]) != null)
                    error("Key \"" + arg + "\" is specified more than once.");

                ++i;
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

    protected abstract void showHelp();

    public final boolean isVerbose()
    {
        return verbose;
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
    public final String get(String key)
    {
        final String value = map.get(key);

        if (value == null)
            error("Missing \"" + key + "\".");

        return value;
    }

    /**
     * Report an error if there was no such key.
     */
    public final File getFile(String key)
    {
        return new File(get(key));
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

    //--------------------------------------------------------------------------

    private boolean verbose = false;
    private String action;
    private Map<String, String> map = new HashMap<String, String>();
}
