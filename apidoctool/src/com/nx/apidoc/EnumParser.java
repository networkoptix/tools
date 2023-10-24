// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.utils.SourceCode;

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

    public EnumParser(SourceCode sourceCode, boolean verbose, int line)
    {
        this.sourceCode = sourceCode;
        this.verbose = verbose;
        this.line = line;
    }

    public static final class EnumInfo
    {
        public static final class Value
        {
            public String name;
            public String description;
            public boolean unused = false;
            public boolean proprietary = false;
            public boolean deprecated = false;
            public String deprecatedDescription = "";
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
                if (value.unused)
                    continue;

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
        Map<String, EnumInfo> enums = parseRegularEnums();
        enums.putAll(parseNxReflectEnums());
        return enums;
    }

    public final EnumInfo parseRegularEnum() throws Error, ApidocTagParser.Error, SourceCode.Error
    {
        final String[] values = sourceCode.matchMultiline(
            line, enumFirstLineRegex, enumHeaderRegex, enumHeaderLastLineRegex);
        if (values == null)
            return null;

        final EnumInfo enumInfo = new EnumInfo();
        enumInfo.name = values[1].trim();
        enumInfo.description = parseEnumDescription();
        enumInfo.values = parseEnumValues();
        return enumInfo;
    }

    private final Map<String, EnumInfo> parseRegularEnums()
        throws Error, SourceCode.Error, ApidocTagParser.Error
    {
        final Map<String, EnumInfo> enums = new HashMap<String, EnumInfo>();
        line = 1;
        while (line <= sourceCode.getLineCount())
        {
            final EnumInfo enumInfo = parseRegularEnum();
            if (enumInfo != null)
                enums.put(enumInfo.name, enumInfo);
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
                if (parseEnumValueDescription(value))
                    values.add(value);
            }
            ++line;
        }
        return values;
    }

    public final EnumInfo parseNxReflectEnum() throws Error, ApidocTagParser.Error
    {
        final String[] match = sourceCode.matchLine(line, nxReflectEnumHeaderRegex);
        if (match == null)
            return null;

        final EnumInfo enumInfo = new EnumInfo();
        enumInfo.name = match[0].trim();
        enumInfo.description = parseEnumDescription();
        enumInfo.values = parseNxReflectEnumValues();
        return enumInfo;
    }

    private final Map<String, EnumInfo> parseNxReflectEnums()
        throws Error, SourceCode.Error, ApidocTagParser.Error
    {
        final Map<String, EnumInfo> enums = new HashMap<String, EnumInfo>();
        line = 1;
        while (line <= sourceCode.getLineCount())
        {
            final EnumInfo enumInfo = parseNxReflectEnum();
            if (enumInfo != null)
                enums.put(enumInfo.name, enumInfo);
            ++line;
        }
        return enums;
    }

    public final int line() { return this.line; }

    /**
     * nx_reflect library provides a set of macros to declare enumerations which could be
     * serialized with no need to do anything else. They look like:
     * ```
     * NX_REFLECTION_ENUM(Enum,
     *     value1,
     *     value2,
     *     value3
     * )
     * ```
     * Enum class is declared with NX_REFLECTION_ENUM_CLASS. Also there are two additional macros
     * for enumerations declared inside a class or a struct: NX_REFLECTION_ENUM_IN_CLASS and
     * NX_REFLECTION_ENUM_CLASS_IN_CLASS.
     */
    private List<EnumInfo.Value> parseNxReflectEnumValues() throws Error, ApidocTagParser.Error
    {
        final List<EnumInfo.Value> values = new ArrayList<EnumInfo.Value>();
        ++line;
        int parenthesesCount = 1; //< The first one was in the header.
        while (line <= sourceCode.getLineCount())
        {
            final String lineStr = sourceCode.getLine(line);
            for (int i = 0; i < lineStr.length(); ++i)
            {
                final char c = lineStr.charAt(i);
                if (c == '(')
                {
                    ++parenthesesCount;
                }
                else if (c == ')')
                {
                    --parenthesesCount;
                    if (parenthesesCount == 0)
                        break;
                }
            }

            final String[] match = sourceCode.matchLine(line, valueRegex);
            if (match != null)
            {
                EnumInfo.Value value = new EnumInfo.Value();
                value.name = match[0];
                if (parseEnumValueDescription(value))
                    values.add(value);
            }

            if (parenthesesCount == 0)
                break;

            ++line;
        }
        return values;
    }

    private String parseEnumDescription() throws Error, ApidocTagParser.Error
    {
        final List<ApidocTagParser.Item> items =
            ApidocTagParser.getItemsForType(sourceCode, line, verbose);
        if (items != null && items.size() > 0)
        {
            for (int i = 1; i < items.size(); ++i)
            {
                if (!items.get(i).getTag().startsWith(ApidocComment.TAG_COMMENTED_OUT))
                    throw new Error("Unexpected tag " + items.get(i).getTag() + " found.");
            }
            return items.get(0).getFullText(0);
        }
        return null;
    }

    /**
     * @return False in case the enum value must be ignored.
     */
    private boolean parseEnumValueDescription(EnumInfo.Value value) throws Error, ApidocTagParser.Error
    {
        final List<ApidocTagParser.Item> items = ApidocTagParser.getItemsForType(sourceCode, line, verbose);

        if (items == null || items.isEmpty())
        {
            value.description = null;
            return true;
        }

        final ApidocTagParser.Item apidocItem = items.get(0);
        value.description = apidocItem.getFullText(0);

        final String apidocAttribute = apidocItem.getAttribute();
        if (!apidocAttribute.isEmpty())
        {
            if (ApidocComment.ATTR_PROPRIETARY.equals(apidocAttribute))
                value.proprietary = true;
            else if (ApidocComment.ATTR_UNUSED.equals(apidocAttribute))
                value.unused = true;
            else
                throw new Error("Unexpected attribute " + apidocAttribute + " in " + apidocItem.getTag() + ".");
        }

        if (items.size() == 1)
            return true; //< No tags follow the description text.

        int itemIndex = 1;

        while (itemIndex < items.size())
        {
            final ApidocTagParser.Item item = items.get(itemIndex);
            if (ApidocComment.TAG_CAPTION.equals(item.getTag()))
            {
                if (!item.getAttribute().isEmpty())
                    throw new Error("Unexpected attribute " + item.getAttribute() + " in " + item.getTag() + ".");

                // Overriding the name with the one specified in `%caption`.
                value.name = item.getInitialToken();

                if (value.name == null || value.name.isEmpty())
                    throw new Error("Missing caption in " + item.getTag() + ".");
                if (!item.getTextAfterInitialToken(/*indentLevel*/ 0).isEmpty())
                    throw new Error("Unexpected text after caption in " + item.getTag() + ".");

                ++itemIndex;
            }
            else if (ApidocComment.TAG_DEPRECATED.equals(item.getTag()))
            {
                value.deprecated = true;
                value.deprecatedDescription = item.getFullText(0);
                ++itemIndex;
            }
            else if (item.getTag().startsWith(ApidocComment.TAG_COMMENTED_OUT))
            {
                ++itemIndex;
            }
            else
            {
                break;
            }
        }
        if (itemIndex < items.size())
            throw new Error("Unexpected tag " + items.get(itemIndex).getTag() + " found.");
        return true;
    }

    private final boolean verbose;
    private final SourceCode sourceCode;
    private int line;

    private static final Pattern enumFirstLineRegex = Pattern.compile(
        " {0,4}enum [^;]*");

    private static final Pattern enumHeaderRegex = Pattern.compile(
        " {0,4}enum\\s+(class\\s+)?([_A-Za-z0-9]+)\\s*\\{");

    private static final Pattern enumHeaderLastLineRegex = Pattern.compile(
        "[^;]*\\{");

    private static final Pattern enumLastLineRegex = Pattern.compile(
        " {0,4}};");

    private static final Pattern nxReflectEnumHeaderRegex = Pattern.compile(
        " {0,4}NX_REFLECTION_ENUM(?:_CLASS)?(?:_IN_CLASS)?\\s*\\(\\s*([_A-Za-z0-9]+)\\s*,");

    private static final Pattern valueRegex = Pattern.compile(
        " {4,8}([_A-Za-z0-9]+)\\s*(=.*)?[,\\s]*.*");
}
