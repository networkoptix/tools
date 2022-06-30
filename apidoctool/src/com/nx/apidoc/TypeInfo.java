package com.nx.apidoc;

import com.nx.util.Utils;

import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public final class TypeInfo
{
    public Apidoc.Type fixed = Apidoc.Type.UNKNOWN;
    public String name;
    public boolean isStdOptional = false;
    public TypeInfo mapValueType = null;
    public static final String mapKeyPlaceholder = "*";

    public void fillFromLabel(final String label) throws Exception
    {
        if (label.startsWith("{") && label.endsWith("}"))
        {
            fillFromNameRecursive(label.substring(/*beginIndex*/ 1, /*endIndex*/ label.length() - 1));
            return;
        }
        fixed = Apidoc.Type.fromString(label);
    }

    public void fillFromName(final String type) throws Exception
    {
        fillFromNameRecursive(type);
    }

    public static String chronoSuffix(final String type)
    {
        return requiredChronoSuffixes.get(type);
    }

    public static String mapItem(final String type) throws Exception
    {
        for (final String mapAlias: mapAliases)
        {
            if (!type.startsWith(mapAlias))
                continue;
            if (!type.endsWith(">"))
                throw new Exception("Invalid type `" + type + "`.");
            final String[] keyValue =
                type.substring(mapAlias.length(), type.length() - ">".length()).split(",");
            if (keyValue.length != 2)
                throw new Exception("Unsupported map type `" + type + "`.");
            final String result = keyValue[1].trim();
            if (result.isEmpty())
                throw new Exception("Invalid type `" + type + "`.");
            return result;
        }
        return null;
    }

    private String arrayItem(final String type) throws Exception
    {
        for (final String arrayAlias: arrayAliases)
        {
            if (!type.startsWith(arrayAlias))
                continue;
            if (!type.endsWith(">"))
                throw new Exception("Invalid type `" + type + "`.");
            if (fixed == Apidoc.Type.ARRAY)
                throw new Exception("Arrays of `" + type + "` are unsupported.");
            final String result =
                type.substring(arrayAlias.length(), type.length() - ">".length()).trim();
            if (result.isEmpty())
                throw new Exception("Invalid type `" + type + "`.");
            return result;
        }
        return null;
    }

    private void fillFromNameRecursive(final String type) throws Exception
    {
        assert fixed == Apidoc.Type.UNKNOWN || fixed == Apidoc.Type.ARRAY;

        String item = null;
        final String chronoSuffix = requiredChronoSuffixes.get(Utils.removeCppNamespaces(type));
        if (chronoSuffix != null)
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.STRING : Apidoc.Type.STRING_ARRAY;
        }
        else if (integerAliases.contains(type))
        {
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.INTEGER;
        }
        else if (typesRepresentedAsJsonString.contains(type))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.STRING : Apidoc.Type.STRING_ARRAY;
        }
        else if (floatAliases.contains(type))
        {
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.FLOAT;
        }
        else if (booleanAliases.contains(type))
        {
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.BOOLEAN;
        }
        else if (uuidAliases.contains(type))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.UUID : Apidoc.Type.UUID_ARRAY;
        }
        else if (type.equals("QJsonValue"))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.ANY : Apidoc.Type.ARRAY;
        }
        else if (type.equals("QStringList"))
        {
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.STRING_ARRAY;
        }
        else if (type.endsWith("List") && !type.equals("QStringList"))
        {
            fixed = Apidoc.Type.ARRAY;
            fillFromNameRecursive(type.substring(0, type.length() - "List".length()));
        }
        else if ((item = this.arrayItem(type)) != null)
        {
            if (typesRepresentedAsJsonString.contains(item))
            {
                if (fixed == Apidoc.Type.UNKNOWN)
                    fixed = Apidoc.Type.STRING_ARRAY;
            }
            else if (uuidAliases.contains(item))
            {
                if (fixed == Apidoc.Type.UNKNOWN)
                    fixed = Apidoc.Type.UUID_ARRAY;
            }
            else
            {
                fixed = Apidoc.Type.ARRAY;
                fillFromNameRecursive(item);
            }
        }
        else if ((item = this.mapItem(type)) != null)
        {
            mapValueType = new TypeInfo();
            mapValueType.fillFromNameRecursive(item);
            if (mapValueType.fixed == Apidoc.Type.ANY)
            {
                fixed = Apidoc.Type.OBJECT;
                mapValueType = null;
            }
        }
        else if (type.startsWith("std::optional<"))
        {
            if (!type.endsWith(">"))
                throw new Exception("Invalid type `" + type + "`.");
            isStdOptional = true;
            fillFromNameRecursive(
                type.substring("std::optional<".length(), type.length() - ">".length()).trim());
        }
        else if (type != null)
        {
            name = type;
        }

        if (name != null)
            name = Utils.removeCppNamespaces(name);
    }

    private static final List<String> integerAliases = Arrays.asList(
        "int", "qint32", "qint16", "qint8");
    private static final List<String> typesRepresentedAsJsonString = Arrays.asList(
        "QString",
        "QnLatin1Array",
        "QByteArray",
        "qint64",
        "size_t",
        "int64_t",
        "std::string",
        "nx::utils::Url");
    private static final List<String> booleanAliases = Arrays.asList("bool");
    private static final List<String> uuidAliases = Arrays.asList("QnUuid");
    private static final List<String> floatAliases = Arrays.asList("float", "qreal");
    private static final List<String> arrayAliases =
        Arrays.asList("std::vector<", "QVector<", "QList<");
    private static final List<String> mapAliases = Arrays.asList("std::map<", "QMap<");
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
