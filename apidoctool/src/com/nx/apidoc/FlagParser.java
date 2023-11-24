// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.utils.SourceCode;

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

    public FlagParser(SourceCode sourceCode, boolean verbose, int line)
    {
        this.sourceCode = sourceCode;
        this.verbose = verbose;
        this.line = line;
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

    public final Map<String, FlagInfo> parseFlags() throws Error, ApidocTagParser.Error
    {
        final Map<String, FlagInfo> flags = new HashMap<String, FlagInfo>();
        while (line <= sourceCode.getLineCount())
        {
            FlagInfo flagInfo = parseFlag();
            if (flagInfo != null)
                flags.put(flagInfo.name, flagInfo);
            ++line;
        }
        return flags;
    }

    public FlagInfo parseFlag() throws Error, ApidocTagParser.Error
    {
        final String[] values = sourceCode.matchLine(line, flagRegex);
        if (values == null)
            return null;

        final FlagInfo flagInfo = new FlagInfo();
        flagInfo.name = values[0].trim();
        flagInfo.enumName = values[1].trim();
        flagInfo.description = parseDescription();
        return flagInfo;
    }

    private String parseDescription() throws Error, ApidocTagParser.Error
    {
        List<ApidocTagParser.Item> items;
        items = ApidocTagParser.getItemsForType(sourceCode, line, verbose);

        if (items != null && items.size() > 0)
        {
            if (items.size() > 1)
                throw new Error("Unexpected tag " + items.get(1).getTag() + " found.");

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
