// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.utils;

import java.io.*;
import java.util.*;
import java.util.regex.Pattern;

/**
 * Base class for keeping named parameters of string type, loaded from a "name=value" file or
 * specified in the command line in the form "-Dname=value".
 *
 * A derived class is expected to define for each param a field initialized with reg*Param(), e.g.:
 *
 * <pre><code>
 *
 *     private static final class MyParams
 *         extends ParamsBase
 *     {
 *         public String myStringParam() { return myStringParam.toString(); }
 *         private final StringBuilder myStringParam = regStringParam("myStringParam",
 *             "default value", "Description of this param.");
 *     }
 *
 * </code></pre>
 */
public abstract class ParamsBase
{
    public void printHelp(PrintStream output, String linePrefix)
    {
        for (int i = 0; i < params.size(); ++i)
        {
            params.get(i).printValue(output, linePrefix);
            if (i < params.size() - 1)
                output.println();
        }
    }

    //---------------------------------------------------------------------------------------------

    protected StringBuilder regStringParam(String name, String defaultValue, String description)
    {
        StringBuilder pValue = new StringBuilder(defaultValue);
        for (final AbstractParam param: params)
        {
            if (param.name.equals(name))
                throw new IllegalArgumentException("Param \"" + name + "\" already registered.");
        }
        params.add(new StringParam(name, description, pValue, defaultValue));
        return pValue;
    }

    public void parse(File optionalFile, List<String> args, boolean verbose)
    {
        if (optionalFile != null)
            parsePropertiesFile(optionalFile);

        parseArgs(args);

        if (verbose)
        {
            System.out.println();
            System.out.println("Using param values:");
            for (AbstractParam param: params)
            {
                final String prefix;
                if (param.isDefault())
                    prefix = "    ";
                else
                    prefix = "  * ";
                System.out.println(prefix + param.name + "=" + param.valueStr());
            }
            System.out.println();
        }
    }

    //---------------------------------------------------------------------------------------------

    private static abstract class AbstractParam
    {
        public final String name;
        public final String description;

        protected AbstractParam(String name, String description)
        {
            this.name = name;
            this.description = description;
        }

        protected abstract String valueStr();
        protected abstract void parse(String s);

        public final void printValue(PrintStream output, String linePrefix)
        {
            if (!description.isEmpty())
            {
                for (final String line: description.split("\n"))
                    output.println(linePrefix + "# " + line);
            }
            output.println(linePrefix + name + "=" + valueStr());
        }

        public abstract boolean isDefault();
    }

    private static final class StringParam
        extends AbstractParam
    {
        public final StringBuilder pValue;
        public final String defaultValue;

        public StringParam(
            String name, String description, StringBuilder pValue, String defaultValue)
        {
            super(name, description);
            this.pValue = pValue;
            this.defaultValue = defaultValue;
        }

        protected String valueStr()
        {
            StringBuilder s = new StringBuilder();
            for (int i = 0; i < pValue.length(); ++i)
            {
                final char c = pValue.charAt(i);
                if (c <= 31 || c >= 126)
                    s.append(String.format("\\u%04X", (int) c));
                else if (c == '\\' || c == ' ')
                    s.append("\\").append(c);
                else
                    s.append(c);
            }
            return s.toString();
        }

        protected void parse(String s)
        {
            pValue.setLength(0);
            pValue.append(s);
        }

        public boolean isDefault()
        {
            return pValue.toString().equals(defaultValue);
        }
    }

    private List<AbstractParam> params = new ArrayList<AbstractParam>();

    //---------------------------------------------------------------------------------------------

    private void parsePropertiesFile(File file)
    {
        Properties properties = new Properties();
        try
        {
            InputStream input = new FileInputStream(file);
            try
            {
                properties.load(input);
            }
            finally
            {
                input.close();
            }

            for (Map.Entry entry: properties.entrySet())
            {
                boolean found = false;
                for (AbstractParam param: params)
                {
                    if (param.name.equals(entry.getKey()))
                    {
                        param.parse((String) entry.getValue());
                        found = true;
                        break;
                    }
                }
                if (!found)
                {
                    throw new IOException(
                        "Unknown property: " + entry.getKey() + "=" + entry.getValue());
                }
            }
        }
        catch (IOException e)
        {
            throw new RuntimeException("ERROR: Unable to read params from file " + file + ": "
                + e.getMessage());
        }
    }

    private static final Pattern argRegex = Pattern.compile(
        "-D([_A-Za-z][_A-Za-z0-9]*)\\s*=(.*)", Pattern.DOTALL);

    private void parseArgs(List<String> args)
    {
        for (String arg: args)
        {
            String[] values = Utils.matchRegex(argRegex, arg);
            if (values == null)
            {
                throw new RuntimeException(
                    "ERROR: Argument does not have the form \"-Dname=value\": [" + arg + "]");
            }

            final String name = values[0];
            final String value = values[1];

            boolean found = false;
            for (AbstractParam param: params)
            {
                if (param.name.equals(name))
                {
                    param.parse(value);
                    found = true;
                    break;
                }
            }

            if (!found)
                throw new RuntimeException("ERROR: Unknown argument: [" + arg + "]");
        }
    }
}
