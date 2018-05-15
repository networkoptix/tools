package com.nx.apidoc;

import com.nx.util.SourceCode;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public final class FlagParser
{
    public final class Error
        extends Exception
    {
        public Error(String message)
        {
            super(sourceCode.getFilename() + ":" + line + ": " + message);
        }
    }

    public FlagParser(SourceCode sourceCode, boolean verbose)
    {
        this.sourceCode = sourceCode;
        this.verbose = verbose;
    }

    public static final class FlagInfo
    {
        public String name;
        public String enumName;
        public String description;

        public final String toString()
        {
            String result = new String();
            result += "Name: " + name + "\n";
            result += "EnumName: " + enumName + "\n";
            if (description != null)
                result += "Description: " + description + "\n";

            return result;
        }
    }

    public final Map<String, FlagInfo> parseFlags() throws Error
    {
        final Map<String, FlagInfo> flags = new HashMap<String, FlagInfo>();
        line = 1;
        while (line <= sourceCode.getLineCount())
        {
            final String[] values = sourceCode.matchLine(line, flagRegex);
            if (values != null)
            {
                final FlagInfo flagInfo = new FlagInfo();
                flagInfo.name = values[0].trim();
                flagInfo.enumName = values[1].trim();
                flagInfo.description = parseDescription();
                flags.put(flagInfo.name, flagInfo);
            }
            ++line;
        }
        return flags;
    }

    private String parseDescription() throws Error
    {
        List<ApidocTagParser.Item> items;
        try
        {
            items = ApidocTagParser.getApidocTags(sourceCode, line, verbose);
        }
        catch(ApidocTagParser.Error e)
        {
            throw new Error(e.getMessage());
        }
        if (items != null && items.size() > 0)
        {
            if (items.size() > 1 || !ApidocComment.TAG_APIDOC.equals(items.get(0).getTag()))
                throw new Error(items.get(0).getErrorPrefix() + "Invalid flag apidoc comment");

            return items.get(0).getFullText(0);
        }
        return null;
    }

    private final boolean verbose;
    private final SourceCode sourceCode;
    private int line;

    private static final Pattern flagRegex = Pattern.compile(
        "\\s*Q_DECLARE_FLAGS\\(([_A-Za-z0-9]+),\\s*([_A-Za-z0-9]+)\\)");
}
