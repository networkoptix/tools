package com.nx.apidoc;

import com.nx.util.SourceCode;
import com.nx.util.Utils;

import java.util.*;
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
            if (items != null && !items.isEmpty())
                return items.get(0).getFullText(0);
            return "";
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

    public StructParser(
        SourceCode sourceCode, boolean verbose, boolean invalidChronoFieldSuffixIsError)
    {
        this.verbose = verbose;
        this.sourceCode = sourceCode;
        this.invalidChronoFieldSuffixIsError = invalidChronoFieldSuffixIsError;
    }

    public final Map<String, StructInfo> parseStructs(Map<String, EnumParser.EnumInfo> enumsInFile)
        throws Error, SourceCode.Error, ApidocTagParser.Error, EnumParser.Error
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
                    final String[] match = sourceCode.matchLine(line, fieldRegex);
                    if (match != null && !"using".equals(match[0]))
                    {
                        final StructInfo.Field field = parseStructField();
                        if (field != null)
                        {
                            if (enums.contains(field.type.name))
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
                final String mapItem = TypeInfo.mapItem(parents);
                if (mapItem == null)
                {
                    for (String base: parents.split(","))
                        struct.baseTypeNames.add(Utils.removeCppNamespaces(base.trim()));
                }
                else
                {
                    struct.baseTypeNames.add(mapItem);
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

    private StructInfo.Field parseStructField() throws ApidocTagParser.Error, Error
    {
        final String[] match = sourceCode.matchLine(line, fieldRegex);
        return match != null && !"using".equals(match[0]) ?
            parseField(match[0], match[1]) : null;
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
        try
        {
            field.type.fillFromName(type);
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

    private static final Pattern fieldRegex = Pattern.compile(
        " {4}((?:::)*\\w+(?:(?:::|<|, )\\w+>*)*)\\s+(\\w+)(?:\\s=\\s.*)?(?:\\s*\\{.*}\\s*)?;.*");
      //     0Type-----------------------------^    1Name Equals------^ Text-in-braces---^
}
