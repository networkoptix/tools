// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.utils.Utils;

import java.util.*;

import org.json.*;

public final class TypeInfo
{
    public Apidoc.Type fixed = Apidoc.Type.UNKNOWN;
    public String name = null;
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

    public void fillMissingType(final TypeInfo origin)
    {
        if (fixed == Apidoc.Type.UNKNOWN)
            fixed = origin.fixed;
        if (name == null)
            name = origin.name;
        if (!isStdOptional)
            isStdOptional = origin.isStdOptional;
        if (!canBeNull)
            canBeNull = origin.canBeNull;
        if (mapValueType == null)
            mapValueType = origin.mapValueType;
        if (variantValueTypes == null)
            variantValueTypes = origin.variantValueTypes;
    }

    public void setFixedChrono(boolean asString)
    {
        if (!isChrono())
            return;
        variantValueTypes = null;
        if (fixed == Apidoc.Type.ARRAY)
        {
            if (asString)
                fixed = Apidoc.Type.STRING_ARRAY;
        }
        else
        {
            fixed = asString ? Apidoc.Type.STRING : Apidoc.Type.INTEGER;
        }
    }

    public static String chronoSuffix(final String type)
    {
        return requiredChronoSuffixes.get(type);
    }

    public boolean isChrono()
    {
        return requiredChronoSuffixes.containsKey(name);
    }

    public Object parse(final String value)
    {
        if (variantValueTypes != null)
        {
            for (int i = 0; i < variantValueTypes.size(); ++i)
            {
                final TypeInfo variantType = variantValueTypes.get(i);
                if (i == variantValueTypes.size() - 1)
                    return variantType.parse(value);
                try
                {
                    return variantType.parse(value);
                }
                catch (Throwable e)
                {
                }
            }
        }
        if (fixed == Apidoc.Type.INTEGER)
            return Integer.parseInt(value);
        if (fixed == Apidoc.Type.BOOLEAN)
            return Boolean.parseBoolean(value);
        if (fixed == Apidoc.Type.FLOAT)
            return Double.parseDouble(value);
        if (fixed == Apidoc.Type.UUID)
            return UUID.fromString(value);
        if (fixed == Apidoc.Type.ARRAY)
            return new JSONArray(value);
        if (fixed == Apidoc.Type.OBJECT)
            return new JSONObject(value);
        if (fixed == Apidoc.Type.ANY)
            return new JSONTokener(value).nextValue();
        return value;
    }

    public String extractMapType(final String type) throws Exception
    {
        for (final String mapAlias: mapAliases)
        {
            if (!type.startsWith(mapAlias))
                continue;
            TypeInfo key = new TypeInfo();
            String nextType = key.extractType(type.substring(mapAlias.length()).trim()).trim();
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

    private String extractVariantType(final String type) throws Exception
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

    private String extractOptionalType(final String type) throws Exception
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
        final String firstType = type.split("[>, ]")[0];
        final String checkType = Utils.removeCppNamespaces(firstType.trim());
        for (final String chronoType: requiredChronoSuffixes.keySet())
        {
            if (!chronoType.equals(checkType))
                continue;
            name = checkType;
            variantValueTypes = new ArrayList<>();
            TypeInfo variantInt = new TypeInfo();
            variantInt.fixed = Apidoc.Type.INTEGER;
            variantValueTypes.add(variantInt);
            TypeInfo variantString = new TypeInfo();
            variantString.fixed = Apidoc.Type.STRING;
            variantValueTypes.add(variantString);
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.OBJECT : Apidoc.Type.ARRAY;
            return type.substring(firstType.length()).trim();
        }
        return null;
    }

    private String extractBasicType(
        final String type, final Apidoc.Type basic, final List<String> aliases)
    {
        final String firstType = type.split("[>, ]")[0];
        final String checkType = firstType.trim();
        for (final String alias: aliases)
        {
            if (!alias.equals(checkType))
                continue;
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = basic;
            else if (basic == Apidoc.Type.STRING)
                fixed = Apidoc.Type.STRING_ARRAY;
            else if (basic == Apidoc.Type.UUID)
                fixed = Apidoc.Type.UUID_ARRAY;
            return type.substring(firstType.length()).trim();
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
        nextType = extractChronoType(type);
        if (nextType != null)
            return nextType;
        for (final Map.Entry<Apidoc.Type, List<String>> basic: basicTypeAliases.entrySet())
        {
            nextType = extractBasicType(type, basic.getKey(), basic.getValue());
            if (nextType != null)
                return nextType;
        }

        final String firstType = type.split("[>, ]")[0];
        final String checkType = firstType.trim();
        if ("QJsonValue".equals(checkType))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.ANY : Apidoc.Type.ARRAY;
        }
        else if ("QJsonObject".equals(checkType))
        {
            fixed = fixed == Apidoc.Type.UNKNOWN ? Apidoc.Type.OBJECT : Apidoc.Type.ARRAY;
        }
        else if ("QJsonArray".equals(checkType))
        {
            fixed = Apidoc.Type.ARRAY;
        }
        else if ("QStringList".equals(checkType))
        {
            if (fixed == Apidoc.Type.UNKNOWN)
                fixed = Apidoc.Type.STRING_ARRAY;
        }
        else if (checkType.endsWith("List"))
        {
            fixed = Apidoc.Type.ARRAY;
            name = Utils.removeCppNamespaces(
                checkType.substring(0, checkType.length() - "List".length()));
        }
        else
        {
            name = Utils.removeCppNamespaces(checkType);
        }
        return type.substring(firstType.length()).trim();
    }

    private static final Map<Apidoc.Type, List<String>> basicTypeAliases =
        new HashMap<Apidoc.Type, List<String>>()
        {
            {
                put(Apidoc.Type.BOOLEAN, Arrays.asList("bool"));
                put(Apidoc.Type.INTEGER, Arrays.asList("int", "qint32", "qint16", "qint8"));
                put(Apidoc.Type.FLOAT, Arrays.asList("float", "qreal"));
                put(Apidoc.Type.UUID, Arrays.asList("QnUuid", "Uuid", "nx::Uuid"));
                put(Apidoc.Type.STRING, Arrays.asList(
                    "QString",
                    "QnLatin1Array",
                    "QByteArray",
                    "qint64",
                    "size_t",
                    "int64_t",
                    "std::string",
                    "nx::utils::Url"));
            }
        };
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
