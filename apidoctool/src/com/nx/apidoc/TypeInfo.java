package com.nx.apidoc;

import com.nx.util.Utils;

import java.util.*;

public final class TypeInfo
{
    public Apidoc.Type fixed = Apidoc.Type.UNKNOWN;
    public String name;
    public boolean isStdOptional = false;
    public boolean canBeNull = false;
    public TypeInfo mapValueType = null;
    public List<TypeInfo> variantValueTypes = null;
    public static final String mapKeyPlaceholder = "*";
    public static final String nullType = "nullptr_t";

    public void fillFromLabel(final String label) throws Exception
    {
        if (label.startsWith("{") && label.endsWith("}"))
        {
            extractType(label.substring(/*beginIndex*/ 1, /*endIndex*/ label.length() - 1));
            return;
        }
        fixed = Apidoc.Type.fromString(label);
    }

    public void fillFromName(final String type) throws Exception
    {
        extractType(type);
    }

    public static String chronoSuffix(final String type)
    {
        return requiredChronoSuffixes.get(type);
    }

    public String extractMapType(final String type) throws Exception
    {
        for (final String mapAlias: mapAliases)
        {
            if (!type.startsWith(mapAlias))
                continue;
            TypeInfo key = new TypeInfo();
            String nextType = key.extractType(type.substring(mapAlias.length()).trim()).trim();
            if (key.fixed != Apidoc.Type.STRING && key.fixed != Apidoc.Type.UUID)
                throw new Exception("Unsupported key type of map `" + type + "`.");
            if (!nextType.startsWith(","))
                throw new Exception("Invalid map `" + type + "`.");
            mapValueType = new TypeInfo();
            String result = mapValueType.extractType(nextType.substring(1).trim()).trim();
            if (!result.startsWith(">"))
                throw new Exception("Invalid map `" + type + "`.");
            if (mapValueType.fixed == Apidoc.Type.ANY)
            {
                fixed = Apidoc.Type.OBJECT;
                mapValueType = null;
            }
            return result.substring(1);
        }
        return null;
    }

    private String extractArrayType(final String type) throws Exception
    {
        for (final String arrayAlias: arrayAliases)
        {
            if (!type.startsWith(arrayAlias))
                continue;
            if (fixed == Apidoc.Type.ARRAY)
                throw new Exception("Arrays of `" + type + "` are unsupported.");
            fixed = Apidoc.Type.ARRAY;
            String result = extractType(type.substring(arrayAlias.length()).trim()).trim();
            if (!result.startsWith(">"))
                throw new Exception("Invalid array `" + type + "`.");
            return result.substring(1);
        }
        return null;
    }

    public String extractVariantType(final String type) throws Exception
    {
        if (!type.startsWith("std::variant<"))
            return null;

        variantValueTypes = new ArrayList<>();
        String nextType = type.substring("std::variant<".length()).trim();
        while (true)
        {
            TypeInfo variantType = new TypeInfo();
            String result = variantType.extractType(nextType).trim();
            if (nullType.equals(variantType.name))
                canBeNull = true;
            else
                variantValueTypes.add(variantType);
            if (result.startsWith(","))
            {
                nextType = result.substring(1).trim();
            }
            else
            {
                if (!result.startsWith(">"))
                    throw new Exception("Invalid variant `" + type + "`.");
                return result.substring(1);
            }
        }
    }

    public String extractOptionalType(final String type) throws Exception
    {
        if (!type.startsWith("std::optional<"))
            return null;

        isStdOptional = true;
        String result = extractType(type.substring("std::optional<".length())).trim();
        if (!result.startsWith(">"))
            throw new Exception("Invalid optional `" + type + "`.");
        return result.substring(1).trim();
    }

    private String extractChronoType(final String type) throws Exception
    {
        final String firstType = type.split("[>, ]")[0].trim();
        for (final String chronoType: requiredChronoSuffixes.keySet())
        {
            if (!chronoType.equals(firstType))
                continue;
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.STRING : Apidoc.Type.STRING_ARRAY;
            return type.substring(chronoType.length()).trim();
        }
        return null;
    }

    private String extractIntegerType(final String type) throws Exception
    {
        final String firstType = type.split("[>, ]")[0].trim();
        for (final String integerType: integerAliases)
        {
            if (!integerType.equals(firstType))
                continue;
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.INTEGER;
            return type.substring(integerType.length()).trim();
        }
        return null;
    }

    private String extractStringType(final String type) throws Exception
    {
        final String firstType = type.split("[>, ]")[0].trim();
        for (final String stringType: typesRepresentedAsJsonString)
        {
            if (!stringType.equals(firstType))
                continue;
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.STRING : Apidoc.Type.STRING_ARRAY;
            return type.substring(stringType.length()).trim();
        }
        return null;
    }

    private String extractFloatType(final String type) throws Exception
    {
        final String firstType = type.split("[>, ]")[0].trim();
        for (final String floatType: floatAliases)
        {
            if (!floatType.equals(firstType))
                continue;
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.FLOAT;
            return type.substring(floatType.length()).trim();
        }
        return null;
    }

    private String extractBooleanType(final String type) throws Exception
    {
        final String firstType = type.split("[>, ]")[0].trim();
        for (final String booleanType: booleanAliases)
        {
            if (!booleanType.equals(firstType))
                continue;
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.BOOLEAN;
            return type.substring(booleanType.length()).trim();
        }
        return null;
    }

    private String extractUuidType(final String type) throws Exception
    {
        final String firstType = type.split("[>, ]")[0].trim();
        for (final String uuidType: uuidAliases)
        {
            if (!uuidType.equals(firstType))
                continue;
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.UUID : Apidoc.Type.UUID_ARRAY;
            return type.substring(uuidType.length()).trim();
        }
        return null;
    }

    private String extractType(final String type) throws Exception
    {
        assert type != null;
        assert fixed == Apidoc.Type.UNKNOWN || fixed == Apidoc.Type.ARRAY;

        String nextType = null;
        nextType = extractMapType(type);
        if (nextType != null)
            return nextType;
        nextType = extractArrayType(type);
        if (nextType != null)
            return nextType;
        nextType = extractVariantType(type);
        if (nextType != null)
            return nextType;
        nextType = extractOptionalType(type);
        if (nextType != null)
            return nextType;
        nextType = extractChronoType(Utils.removeCppNamespaces(type));
        if (nextType != null)
            return nextType;
        nextType = extractIntegerType(type);
        if (nextType != null)
            return nextType;
        nextType = extractStringType(type);
        if (nextType != null)
            return nextType;
        nextType = extractFloatType(type);
        if (nextType != null)
            return nextType;
        nextType = extractBooleanType(type);
        if (nextType != null)
            return nextType;
        nextType = extractUuidType(type);
        if (nextType != null)
            return nextType;

        final String firstType = type.split("[>, ]")[0].trim();
        if ("QJsonValue".equals(firstType))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.ANY : Apidoc.Type.ARRAY;
        }
        else if ("QJsonObject".equals(firstType))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.OBJECT : Apidoc.Type.ARRAY;
        }
        else if ("QJsonArray".equals(firstType))
        {
            fixed = Apidoc.Type.ARRAY;
        }
        else if ("QStringList".equals(firstType))
        {
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.STRING_ARRAY;
        }
        else if (firstType.endsWith("List"))
        {
            fixed = Apidoc.Type.ARRAY;
            name = Utils.removeCppNamespaces(
                firstType.substring(0, firstType.length() - "List".length()));
        }
        else
        {
            name = Utils.removeCppNamespaces(firstType);
        }
        return type.substring(firstType.length()).trim();
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
