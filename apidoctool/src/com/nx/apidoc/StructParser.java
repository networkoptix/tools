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
            for (Field field : fields)
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

    public StructParser(SourceCode sourceCode, boolean verbose)
    {
        this.verbose = verbose;
        this.sourceCode = sourceCode;
    }

    public final Map<String, StructInfo> parseStructs()
        throws Error, SourceCode.Error, ApidocTagParser.Error
    {
        final Map<String, StructInfo> structs = new HashMap<String, StructInfo>();
        line = 1;
        while (line <= sourceCode.getLineCount())
        {
            final String[] values = sourceCode.matchMultiline(
                line, structFirstLineRegex, structHeaderRegex, structHeaderLastLineRegex);
            if (values != null)
            {
                StructInfo struct = parseStructHeader(values[0]);
                struct.fields = parseStructFields();
                structs.put(struct.name, struct);
            }
            ++line;
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

    private List<StructInfo.Field> parseStructFields()
        throws ApidocTagParser.Error
    {
        final List<StructInfo.Field> fields = new ArrayList<StructInfo.Field>();
        while (line <= sourceCode.getLineCount())
        {
            if (sourceCode.lineMatches(line, structLastLineRegex))
                return fields;

            final String[] match = sourceCode.matchLine(line, fieldRegex);
            if (match != null && !"using".equals(match[0]))
                fields.add(parseField(match[0], match[1]));

            ++line;
        }
        return fields;
    }

    private StructInfo.Field parseField(String type, String name)
        throws ApidocTagParser.Error
    {
        final StructInfo.Field field = new StructInfo.Field();
        field.name = name;
        if (integerAliases.contains(type))
        {
            field.type = Apidoc.Type.INTEGER;
        }
        else if (stringAliases.contains(type))
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
        else if (type.endsWith("List"))
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
            field.type = Apidoc.Type.ARRAY;
            field.typeName = type.substring(
                "std::vector<".length(), type.length() - ">".length()).trim();
        }
        else
        {
            field.type = Apidoc.Type.UNKNOWN;
            field.typeName = type;
        }

        if (field.typeName != null)
            field.typeName = Utils.removeCppNamespaces(field.typeName);

        field.items = ApidocTagParser.getItemsForType(sourceCode, line, verbose);;
        return field;
    }

    private final SourceCode sourceCode;
    private final boolean verbose;
    private int line;

    private static final List<String> integerAliases = Arrays.asList(
        "int", "qint32", "qint16", "qint8", "qint64");
    private static final List<String> stringAliases = Arrays.asList(
        "QString", "QnLatin1Array", "QByteArray");
    private static final List<String> booleanAliases = Arrays.asList("bool");
    private static final List<String> uuidAliases = Arrays.asList("QnUuid");
    private static final List<String> floatAliases = Arrays.asList("float");

    private static final Pattern structFirstLineRegex = Pattern.compile(
        "struct [^;]*");

    private static final Pattern structHeaderRegex = Pattern.compile(
        "struct ([^;]*)\\{");

    private static final Pattern structHeaderLastLineRegex = Pattern.compile(
        "[^;]*\\{");

    private static final Pattern structLastLineRegex = Pattern.compile(
        "};");

    private static final Pattern fieldRegex = Pattern.compile(
        "    ([_A-Za-z0-9:<>]+)\\s+([_A-Za-z0-9]+)(\\s=\\s.*)?(\\s*\\{.*}\\s*)?;.*");
}
