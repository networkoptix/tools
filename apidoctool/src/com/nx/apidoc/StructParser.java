// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.utils.SourceCode;
import com.nx.utils.Utils;

import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class StructParser
{
    public final class Error
        extends Exception
    {
        public Error(String message)
        {
            super(sourceCode.getFilename() + ":" + line + ": " + message);
        }
    }

    public static final class StructInfo
    {
        public static final class Field
        {
            public String name;
            public TypeInfo type = new TypeInfo();
            public List<ApidocTagParser.Item> items;
        }

        public String name;
        public List<String> baseTypeNames;
        public List<Field> fields;
        public List<ApidocTagParser.Item> items;
        public boolean isMap = false;

        public final String description()
        {
            if (items == null)
                return "";
            for (ApidocTagParser.Item item: items)
            {
                if (ApidocComment.TAG_APIDOC.equals(item.getTag()))
                {
                    final String description = item.getFullText(0);
                    if (!description.trim().isEmpty())
                        return description;
                }
            }
            return "";
        }

        public void fillParamAttributes(Apidoc.Param param)
        {
            if (items == null)
                return;

            for (ApidocTagParser.Item item: items)
            {
                if (ApidocComment.TAG_APIDOC.equals(item.getTag()))
                {
                    final String attribute = item.getAttribute();
                    if (!param.immutable && ApidocComment.ATTR_IMMUTABLE.equals(attribute))
                        param.immutable = true;
                    if (!param.optional && ApidocComment.ATTR_OPT.equals(attribute))
                        param.optional = true;
                    if (!param.proprietary && ApidocComment.ATTR_PROPRIETARY.equals(attribute))
                        param.proprietary = true;
                    if (!param.readonly && ApidocComment.ATTR_READONLY.equals(attribute))
                        param.readonly = true;
                    if (!param.unused && ApidocComment.ATTR_UNUSED.equals(attribute))
                        param.unused = true;
                    break;
                }
            }
        }

        public final String toString()
        {
            String result = "";
            result += "Name: " + name + "\n";
            result += "Parents: " + baseTypeNames + "\n";
            if (items != null)
            {
                for (ApidocTagParser.Item item : items)
                    result += "Apidoc item: \"" + item.getFullText(0) + "\"\n";
            }
            for (Field field: fields)
            {
                result += "    Field:" + field.type.fixed.toString();
                if (field.type.name != null)
                    result += "(" + field.type.name + ")";
                result += " " + field.name + "\n";

                if (field.items != null)
                {
                    for (ApidocTagParser.Item item : field.items)
                        result += "    Apidoc item: \"" + item.getFullText(0) + "\"\n";
                }
            }
            return result;
        }
    }

    private static class CollectResult
    {
        final String text;
        final int lastLine;
        CollectResult(String text, int lastLine)
        {
            this.text = text;
            this.lastLine = lastLine;
        }
    }

    public StructParser(
        SourceCode sourceCode, boolean verbose, boolean invalidChronoFieldSuffixIsError)
    {
        this.verbose = verbose;
        this.sourceCode = sourceCode;
        this.invalidChronoFieldSuffixIsError = invalidChronoFieldSuffixIsError;
    }

    public final Map<String, StructInfo> parseStructs(
        Map<String, EnumParser.EnumInfo> enumsInFile, Map<String, FlagParser.FlagInfo> flagsInFile)
        throws Error, SourceCode.Error, ApidocTagParser.Error, EnumParser.Error, FlagParser.Error
    {
        final Map<String, StructInfo> structs = new HashMap<String, StructInfo>();
        for (line = 1; line <= sourceCode.getLineCount(); ++line)
        {
            final String[] values = sourceCode.matchMultiline(
                line, structFirstLineRegex, structHeaderRegex, structHeaderLastLineRegex);
            if (values == null)
                continue;

            final StructInfo struct = parseStructHeader(values[0]);
            struct.fields = new ArrayList<StructInfo.Field>();
            final Set<String> enums = new HashSet<String>();
            final Set<String> flags = new HashSet<String>();
            for (++line; line <= sourceCode.getLineCount(); ++line)
            {
                if (sourceCode.lineMatches(line, structLastLineRegex))
                    break;

                EnumParser enumParser = new EnumParser(sourceCode, verbose, line);
                EnumParser.EnumInfo enumInfo = enumParser.parseRegularEnum();
                if (enumInfo == null)
                    enumInfo = enumParser.parseNxReflectEnum();
                if (enumInfo != null)
                {
                    final EnumParser.EnumInfo parsedEnum = enumsInFile.get(enumInfo.name);
                    if (parsedEnum != null && parsedEnum.toString().equals(enumInfo.toString()))
                        enumsInFile.remove(enumInfo.name);
                    enums.add(enumInfo.name);
                    enumInfo.name = struct.name + "_" + enumInfo.name;
                    enumsInFile.put(enumInfo.name, enumInfo);
                    line = enumParser.line();
                }
                else
                {
                    FlagParser flagParser = new FlagParser(sourceCode, verbose, line);
                    FlagParser.FlagInfo flagInfo = flagParser.parseFlag();
                    if (flagInfo != null)
                    {
                        final FlagParser.FlagInfo parsedFlag = flagsInFile.get(flagInfo.name);
                        if (parsedFlag != null && parsedFlag.toString().equals(flagInfo.toString()))
                            flagsInFile.remove(flagInfo.name);
                        flags.add(flagInfo.name);
                        flagInfo.name = struct.name + "_" + flagInfo.name;
                        flagInfo.enumName = struct.name + "_" + flagInfo.enumName;
                        flagsInFile.put(flagInfo.name, flagInfo);
                        ++line;
                    }
                    else
                    {
                        String[] match = sourceCode.matchLine(line, fieldRegex);

                        String currLine = sourceCode.getLine(line);
                        // Not a full match, but looks like the start of a match.  Start multi-line logic
                        if (match == null && prefixRegex.matcher(currLine).find())
                        {
                            CollectResult r = collectUntilSemicolon(line);
                            String merged = "    " + r.text.replaceAll("\\s+", " ");
                            Matcher m = fieldRegex.matcher(merged);

                            if (m.matches())
                            {
                                match = new String[]{ m.group(1), m.group(2) };
                                line = r.lastLine;
                            }
                        }

                        if (match != null && !"using".equals(match[0]))
                        {
                            StructInfo.Field field = parseField(match[0], match[1]);
                            if (enums.contains(field.type.name) || flags.contains(field.type.name))
                                field.type.name = struct.name + "_" + field.type.name;
                            struct.fields.add(field);
                        }
                    }
                }
            }

            structs.put(struct.name, struct);
        }

        return structs;
    }

    private CollectResult collectUntilSemicolon(int startLine) throws Error
    {
        StringBuilder sb = new StringBuilder();
        int total = sourceCode.getLineCount();
        int current = startLine;

        while (current  < total)
        {
            String raw = sourceCode.getLine(current);
            int idx = raw.indexOf("//");
            String noComment = (idx >= 0 ? raw.substring(0, idx) : raw).trim();

            sb.append(noComment);
            if (noComment.endsWith(";"))
                break;

            current++;
        }
        String result = sb.toString().trim();

        if (current == total && !result.endsWith(";"))
            throw new Error("Was unable to parse a multiline type before hitting the end of the file.");

        result = result.replaceAll(",", ", ");
        return new CollectResult(result, current);
    }

    private StructInfo parseStructHeader(String header) throws Error, ApidocTagParser.Error
    {
        final StructInfo struct = new StructInfo();
        final String[] items = header.split(":\\s");
        if (items.length > 2)
             throw new Error("Too many inheritance symbols \':\'");

        if (items.length == 2)
        {
            String parents = items[1];
            parents = parents.replace("public", "");
            parents = parents.replace("private", "");
            parents = parents.replace("protected", "");
            parents = parents.trim();
            struct.baseTypeNames = new ArrayList<String>();
            try
            {
                final TypeInfo map = new TypeInfo();
                map.extractMapType(parents);
                if (map.mapValueType == null)
                {
                    for (String base: parents.split(","))
                        struct.baseTypeNames.add(Utils.removeCppNamespaces(base.trim()));
                }
                else
                {
                    if (map.mapValueType.name != null)
                        struct.baseTypeNames.add(map.mapValueType.name);
                    struct.isMap = true;
                }
            }
            catch (Exception e)
            {
                throw new Error(e.getMessage());
            }
        }

        final String[] nameTokens = items[0].split("\\s");
        struct.name = nameTokens[nameTokens.length - 1]; //< ignore all preceding tokens
        struct.items = ApidocTagParser.getItemsForType(sourceCode, line, verbose);

        return struct;
    }

    private static boolean hasDeprecatedTag(List<ApidocTagParser.Item> items)
    {
        if (items == null)
            return false;
        for (final ApidocTagParser.Item item: items)
        {
            if (ApidocCommentParser.TAG_DEPRECATED.equals(item.getTag()))
                return true;
        }
        return false;
    }

    private StructInfo.Field parseField(String type, String name)
        throws ApidocTagParser.Error, Error
    {
        final StructInfo.Field field = new StructInfo.Field();
        field.name = name;
        field.items = ApidocTagParser.getItemsForType(sourceCode, line, verbose);
        boolean overridden = false;
        if (field.items != null && !field.items.isEmpty())
        {
            final ApidocTagParser.Item item = field.items.get(0);
            if (ApidocComment.TAG_APIDOC.equals(item.getTag()))
            {
                final String label = field.items.get(0).getLabel();
                if (label != null && !label.isEmpty())
                {
                    try
                    {
                        field.type.fillFromLabel(label);
                    }
                    catch (Exception e)
                    {
                        throw new Error("Invalid overridden type \"" + label + "\" for field \"" +
                            type + " " + name + "\" found: " + e.getMessage() + ".");
                    }
                    overridden = field.type.isParsed();
                }
            }
        }

        try
        {
            if (overridden)
            {
                TypeInfo typeInfo = new TypeInfo();
                typeInfo.extractOptionalType(type);
                if (!field.type.isStdOptional)
                    field.type.isStdOptional = typeInfo.isStdOptional;
            }
            else
            {
                field.type.fillFromName(type);
            }
        }
        catch (Exception e)
        {
            throw new Error(e.getMessage());
        }
        final String chronoSuffix = TypeInfo.chronoSuffix(field.type.name);
        if (chronoSuffix != null
            && invalidChronoFieldSuffixIsError
            && !name.endsWith(chronoSuffix)
            && !hasDeprecatedTag(field.items))
        {
            throw new Error(
                "`" + type + " " + name + "` must end with '" + chronoSuffix + "' suffix.");
        }
        return field;
    }

    private final SourceCode sourceCode;
    private final boolean verbose;
    private final boolean invalidChronoFieldSuffixIsError;
    private int line;

    private static final Pattern structFirstLineRegex = Pattern.compile(
        "struct [^;]*");

    private static final Pattern structHeaderRegex = Pattern.compile(
        "struct ([^;]*)\\{");

    private static final Pattern structHeaderLastLineRegex = Pattern.compile(
        "[^;]*\\{");

    private static final Pattern structLastLineRegex = Pattern.compile(
        "};");

    private static final Pattern prefixRegex = Pattern.compile(
        "^ {4}((?:::)*\\w+(?:(?:::|<|, )\\w+)*)");

    private static final Pattern fieldRegex = Pattern.compile(
        " {4}((?:::)*\\w+(?:(?:::|<|, )\\w+>*)*)\\s+(\\w+)(?:\\s=\\s.*)?(?:\\s*\\{.*}\\s*)?;.*");
      //     0Type-----------------------------^    1Name Equals------^ Text-in-braces---^
}
