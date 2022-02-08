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
            public Apidoc.Type type;
            public String typeName;
            public List<ApidocTagParser.Item> items;
            public boolean isStdOptional = false; ///< whether the field is std::optional
        }

        public String name;
        public List<String> baseTypeNames;
        public List<Field> fields;
        public List<ApidocTagParser.Item> items;

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
                result += "    Field:" + field.type.toString();
                if (field.typeName != null)
                    result += "(" + field.typeName + ")";
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
                            if (enums.contains(field.typeName))
                                field.typeName = struct.name + "_" + field.typeName;
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
            struct.baseTypeNames = new ArrayList<String>();
            for (String base: items[1].split(","))
            {
                base = base.replace("public", "");
                base = base.replace("private", "");
                base = base.replace("protected", "");
                struct.baseTypeNames.add(Utils.removeCppNamespaces(base.trim()));
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

        final String chronoSuffix = requiredChronoSuffixes.get(Utils.removeCppNamespaces(type));
        if (chronoSuffix != null)
        {
            if (invalidChronoFieldSuffixIsError && !name.endsWith(chronoSuffix)
                && !hasDeprecatedTag(field.items))
            {
                throw new Error(
                    "`" + type + " " + name + "` must end with '" + chronoSuffix + "' suffix.");
            }
            field.type = Apidoc.Type.STRING;
        }
        else if (integerAliases.contains(type))
        {
            field.type = Apidoc.Type.INTEGER;
        }
        else if (typesRepresentedAsJsonString.contains(type))
        {
            field.type = Apidoc.Type.STRING;
        }
        else if (floatAliases.contains(type))
        {
            field.type = Apidoc.Type.FLOAT;
        }
        else if (booleanAliases.contains(type))
        {
            field.type = Apidoc.Type.BOOLEAN;
        }
        else if (uuidAliases.contains(type))
        {
            field.type = Apidoc.Type.UUID;
        }
        else if (type.equals("QStringList"))
        {
            field.type = Apidoc.Type.STRING_ARRAY;
            field.typeName = "QString";
        }
        else if (type.endsWith("List") && !type.equals("QStringList"))
        {
            field.type = Apidoc.Type.ARRAY;
            field.typeName = type.substring(0, type.length() - "List".length());
        }
        else if (type.equals("std::vector<QnUuid>"))
        {
            field.type = Apidoc.Type.UUID_ARRAY;
        }
        else if (type.startsWith("std::vector<"))
        {
            field.typeName = type.substring(
                "std::vector<".length(), type.length() - ">".length()).trim();
            if (typesRepresentedAsJsonString.contains(field.typeName))
                field.type = Apidoc.Type.STRING_ARRAY;
            else
                field.type = Apidoc.Type.ARRAY;
        }
        else if (type.startsWith("std::optional<"))
        {
            final StructInfo.Field optField = parseField(
                type.substring("std::optional<".length(), type.length() - ">".length()).trim(),
                name);
            optField.isStdOptional = true;
            return optField;
        }
        else
        {
            field.type = Apidoc.Type.UNKNOWN;
            field.typeName = type;
        }

        if (field.typeName != null)
            field.typeName = Utils.removeCppNamespaces(field.typeName);

        return field;
    }

    private final SourceCode sourceCode;
    private final boolean verbose;
    private final boolean invalidChronoFieldSuffixIsError;
    private int line;

    private static final List<String> integerAliases = Arrays.asList(
        "int", "qint32", "qint16", "qint8");
    private static final List<String> typesRepresentedAsJsonString = Arrays.asList(
        "QString", "QnLatin1Array", "QByteArray", "qint64", "size_t", "int64_t", "std::string");
    private static final List<String> booleanAliases = Arrays.asList("bool");
    private static final List<String> uuidAliases = Arrays.asList("QnUuid");
    private static final List<String> floatAliases = Arrays.asList("float", "qreal");

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

    private static final Map<String, String> requiredChronoSuffixes = new HashMap<String, String>()
    {
        {
            put("seconds", "S");
            put("milliseconds", "Ms");
            put("microseconds", "Us");
            put("nanoseconds", "Ns");
            put("minutes", "M");
            put("hours", "H");
            put("time_point", "Ms");
        }
    };
}
