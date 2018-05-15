package com.nx.apidoc;

import com.nx.util.SourceCode;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Pattern;

public final class EnumParser
{
    public final class Error
        extends Exception
    {
        public Error(String message)
        {
            super(sourceCode.getFilename() + ":" + line + ": " + message);
        }
    }

    public EnumParser(SourceCode sourceCode, boolean verbose)
    {
        this.sourceCode = sourceCode;
        this.verbose = verbose;
    }

    public static final class EnumInfo
    {
        public static final class Value
        {
            public String name;
            public String description;
        }

        public String name;
        public List<Value> values;
        public String description;

        public String toString()
        {
            String result = new String();
            result += "Name: " + name + "\n";
            if (description != null)
                result += "Description: " + description + "\n";
            for (Value value: values)
            {
                result += "    Value: " + value.name + "\n";
                if (value.description != null)
                    result += "    Description: " + value.description + "\n";
            }
            return result;
        }
    }
    
    public final Map<String, EnumInfo> parseEnums()
        throws Error, SourceCode.Error, ApidocTagParser.Error
    {
        final Map<String, EnumInfo> enums = new HashMap<String, EnumInfo>();
        line = 1;
        while (line <= sourceCode.getLineCount())
        {
            final String[] values = sourceCode.matchMultiline(
                line, enumFirstLineRegex, enumHeaderRegex, enumHeaderLastLineRegex);
            if (values != null)
            {
                final EnumInfo enumInfo = new EnumInfo();
                enumInfo.name = values[1].trim();
                enumInfo.description = parseDescription();
                enumInfo.values = parseEnumValues();
                enums.put(enumInfo.name, enumInfo);
            }
            ++line;
        }
        return enums;
    }

    private List<EnumInfo.Value> parseEnumValues() throws Error, ApidocTagParser.Error
    {
        final List<EnumInfo.Value> values = new ArrayList<EnumInfo.Value>();
        ++line;
        while (line <= sourceCode.getLineCount())
        {
            if (sourceCode.lineMatches(line, enumLastLineRegex))
                return values;

            final String[] match = sourceCode.matchLine(line, valueRegex);
            if (match != null)
            {
                EnumInfo.Value value = new EnumInfo.Value();
                value.name = match[0];
                value.description = parseDescription();
                values.add(value);
            }
            ++line;
        }
        return values;
    }

    private String parseDescription() throws Error, ApidocTagParser.Error
    {
        final List<ApidocTagParser.Item> items =
            ApidocTagParser.getItemsForType(sourceCode, line, verbose);
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

    private static final Pattern enumFirstLineRegex = Pattern.compile(
        " {0,4}enum .*");

    private static final Pattern enumHeaderRegex = Pattern.compile(
        " {0,4}enum\\s+(class\\s+)?([_A-Za-z0-9]+)\\s*\\{");

    private static final Pattern enumHeaderLastLineRegex = Pattern.compile(
        "[^;]*\\{");

    private static final Pattern enumLastLineRegex = Pattern.compile(
        " {0,4}};");

    private static final Pattern valueRegex = Pattern.compile(
        " {4,8}([_A-Za-z0-9]+)\\s*(=.*)?[,\\s]*.*");
}
