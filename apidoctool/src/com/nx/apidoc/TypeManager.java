// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoc;

import com.nx.utils.SourceCode;

import java.io.File;
import java.io.IOException;
import java.util.*;

public final class TypeManager
{
    public class Error
        extends Exception
    {
        public Error(String message) { super(message); }
    }

    public TypeManager(boolean verbose)
    {
        this.verbose = verbose;
    }

    public final void processFiles(List<File> files, boolean invalidChronoFieldSuffixIsError)
        throws Error, IOException, EnumParser.Error, SourceCode.Error, ApidocTagParser.Error,
            FlagParser.Error, StructParser.Error
    {
        for (File file: files)
        {
            final SourceCode sourceCode = new SourceCode(file);

            final EnumParser enumParser = new EnumParser(sourceCode, verbose, 1);
            final Map<String, EnumParser.EnumInfo> enumsInFile = enumParser.parseEnums();

            final FlagParser flagParser = new FlagParser(sourceCode, verbose, /*line*/ 1);
            final Map<String, FlagParser.FlagInfo> flagsInFile = flagParser.parseFlags();

            final StructParser structParser =
                new StructParser(sourceCode, verbose, invalidChronoFieldSuffixIsError);
            final Map<String, StructParser.StructInfo> structsInFile =
                structParser.parseStructs(enumsInFile, flagsInFile);
            throwIfIntersects(structsInFile.keySet(), structs.keySet(), "structs", file);
            structs.putAll(structsInFile);

            throwIfIntersects(enumsInFile.keySet(), enums.keySet(), "enums", file);
            enums.putAll(enumsInFile);

            throwIfIntersects(flagsInFile.keySet(), flags.keySet(), "flags", file);
            flags.putAll(flagsInFile);
        }
        makeStructsFlat();
        correctTypes();
    }

    public final void mergeDescription(
        TypeInfo inputType, TypeInfo outputType, Apidoc.Function function) throws Error
    {
        if (outputType != null)
        {
            function.result.params = mergeStructParams(
                outputType,
                function.result.params,
                function.result.unusedParams);
            if (function.result.caption.isEmpty())
            {
                // Take the function result caption from the output struct description.
                function.result.caption = getStructDescription(outputType);
            }
        }

        if (inputType != null)
        {
            function.input.params = mergeStructParams(
                inputType,
                function.input.params,
                function.input.unusedParams);
        }
    }

    public List<Apidoc.Param> getStructParams(
        TypeInfo type, String prefix, ApidocCommentParser.ParamDirection paramDirection)
        throws Error
    {
        correctType(type);
        return structToParams(prefix, type, paramDirection, new ArrayList<>(), new HashMap<>());
    }

    /**
     * @return Empty string if the struct was not found, or has no description.
     */
    public String getStructDescription(TypeInfo type) throws Error
    {
        if (!(type.fixed == Apidoc.Type.OBJECT || type.fixed == Apidoc.Type.ARRAY)
            || (type.name == null && type.mapValueType == null))
        {
            return "";
        }
        if (type.mapValueType != null)
            return getStructDescription(type.mapValueType);
        StructParser.StructInfo structInfo = structInfo(type);
        if (structInfo == null)
            return "";
        return structInfo.description();
    }

    private void throwIfIntersects(Set<String> current, Set<String> all, String setType, File file)
        throws Error
    {
        final HashSet<String> copy = new HashSet<String>(current);
        if (copy.retainAll(all) && !copy.isEmpty())
        {
            throw new Error("Found " + setType + ": " + copy +
                " intersection in file " + file);
        }
    }

    private StructParser.StructInfo structOrMapInfo(TypeInfo type)
    {
        return type.mapValueType == null ? structInfo(type) : structOrMapInfo(type.mapValueType);
    }

    private StructParser.StructInfo structInfo(TypeInfo type)
    {
        assert type.mapValueType == null;
        if (type.isChrono())
        {
            final StructParser.StructInfo result = new StructParser.StructInfo();
            result.name = type.name;
            result.fields = new ArrayList<>();
            return result;
        }

        return structs.get(type.name);
    }

    private List<Apidoc.Param> mergeStructParams(
        TypeInfo type,
        List<Apidoc.Param> functionParams,
        List<Apidoc.Param> unusedParams)
        throws Error
    {
        List<Apidoc.Param> structParams = getStructParams(
            type, /*prefix*/ "", ApidocCommentParser.ParamDirection.Input);

        final List<Apidoc.Param> mergedParams = new ArrayList<Apidoc.Param>();
        for (Apidoc.Param structParam: structParams)
        {
            if (!structParam.name.equals(ApidocComment.PARAM_ORDER_BY))
            {
                if (structParam.unused)
                    continue;
                if (findParam(unusedParams, structParam.name) != null) //< Skip unused params.
                    continue;
            }
            boolean isUnusedStructParam = false;
            for (Apidoc.Param unusedParam: unusedParams)
            {
                if (structParam.name.startsWith(unusedParam.name + '.')
                    || structParam.name.startsWith(unusedParam.name + "[]."))
                {
                    isUnusedStructParam = true;
                    break;
                }
            }
            if (isUnusedStructParam)
                continue;

            final Apidoc.Param functionParam = findParam(functionParams, structParam.name);

            if (structParam.type.fixed == Apidoc.Type.UNKNOWN
                && functionParam != null
                && functionParam.type.fixed == Apidoc.Type.UNKNOWN
                && !structParam.hasDefaultDescription)
            {
                throw new Error("Param type not found: \"" + structParam.name
                    + "\" in struct \"" + type.name + "\"");
            }
            if (functionParam != null)
            {
                functionParam.fillMissingFieldsFrom(structParam);
                functionParam.normalizeProperties();

                mergedParams.add(functionParam);
                if (functionParam.type.fixed == Apidoc.Type.OBJECT_JSON
                    || functionParam.type.fixed == Apidoc.Type.ARRAY_JSON)
                {
                    final boolean isArray = functionParam.type.fixed == Apidoc.Type.ARRAY_JSON;
                    mergeObjectJsons(
                        functionParam.name, isArray, functionParams, structParams, mergedParams);
                }
            }
            else
            {
                structParam.normalizeProperties();
                mergedParams.add(structParam);
            }
        }

        // Check redundant params in function comment.
        for (Apidoc.Param param: functionParams)
        {
            if (param.name.equals("format"))
                mergedParams.add(0, param);

            if (findParam(mergedParams, param.name) == null)
            {
                // Ignore built-in parameters starting with the "_" prefix and not present in structs.
                if (verbose && !param.name.startsWith("_"))
                {
                    System.out.println(
                        "WARNING: Param in function apidoc comment: \"" + param.name
                            + "\" not found in structure: " + type.name);
                }
                mergedParams.add(param);
            }
        }

        Apidoc.Param unusedOrderBy = findParam(unusedParams, ApidocComment.PARAM_ORDER_BY);
        if (unusedOrderBy != null)
            mergedParams.add(unusedOrderBy);

        return mergedParams;
    }

    private void mergeObjectJsons(
        String paramName,
        boolean isArray,
        List<Apidoc.Param> functionParams,
        List<Apidoc.Param> structParams,
        List<Apidoc.Param> merged)
    {
        if (isArray)
            paramName += "[]";
        paramName += ".";

        for (Apidoc.Param structParam: structParams)
        {
            if (structParam.name.startsWith(paramName))
            {
                final Apidoc.Param functionParam = findParam(functionParams, structParam.name);
                if (functionParam == null)
                    merged.add(structParam);
            }
        }
        for (Apidoc.Param functionParam: functionParams)
        {
            if (functionParam.name.startsWith(paramName))
                merged.add(functionParam);
        }
    }

    /**
     * @param overriddenParams Used for recursion only; supply an empty list.
     * @param processedStructs Used for recursion only; supply an empty list.
     */
    private List<Apidoc.Param> structToParams(
        String namePrefix,
        TypeInfo type,
        ApidocCommentParser.ParamDirection paramDirection,
        List<Apidoc.Param> overriddenParams,
        HashMap<String, String> processedStructs)
        throws Error
    {
        List<Apidoc.Param> structParams = new ArrayList<>();
        if (type.fixed == Apidoc.Type.ARRAY && !namePrefix.isEmpty())
            namePrefix += "[]";

        if (!namePrefix.isEmpty())
            namePrefix += '.';
        if (type.variantValueTypes != null)
        {
            if (type.isChrono())
                return structParams;
            namePrefix += '#';
            for (int i = 0; i < type.variantValueTypes.size(); ++i)
            {
                final TypeInfo subType = type.variantValueTypes.get(i);
                if (subType.variantValueTypes == null
                    && subType.mapValueType == null
                    && (subType.name == null || TypeInfo.nullType.equals(subType.name)))
                {
                    Apidoc.Param param = new Apidoc.Param();
                    param.isGeneratedFromStruct = true;
                    param.name = namePrefix + i;
                    param.type.fillMissingType(subType);
                    if (subType.isStdOptional)
                        param.optional = true;
                    if (subType.fixed == Apidoc.Type.ENUM || subType.fixed == Apidoc.Type.FLAGS)
                        enumToParam(param, subType.name);
                    structParams.add(param);
                    continue;
                }
                structParams.addAll(structToParams(
                    namePrefix + i, subType, paramDirection, overriddenParams, processedStructs));
            }
            return structParams;
        }

        if (type.mapValueType != null)
        {
            if (type.mapKeyType.fixed == Apidoc.Type.ENUM)
            {
                Apidoc.Param enumParam = new Apidoc.Param();
                enumToParam(enumParam, type.mapKeyType.name);
                for (final Apidoc.Value value: enumParam.values)
                {
                    if (value.unused)
                        continue;

                    final String name = namePrefix + value.name;
                    Apidoc.Param param = new Apidoc.Param();
                    param.name = name;
                    param.type = type.mapValueType;
                    param.optional = true;
                    param.deprecated = value.deprecated;
                    param.deprecatedDescription = value.deprecatedDescription;
                    param.proprietary = value.proprietary;
                    param.description = value.description;
                    if (param.type.name != null)
                    {
                        if (param.type.fixed == Apidoc.Type.ENUM || param.type.fixed == Apidoc.Type.FLAGS)
                        {
                            enumToParam(param, param.type.name);
                        }
                        else
                        {
                            param.recursiveName = processedStructs.get(param.type.name);
                            final StructParser.StructInfo fieldStructInfo = structs.get(param.type.name);
                            if (fieldStructInfo != null)
                                fieldStructInfo.fillParamAttributes(param);
                            if (param.description == null || param.description.isEmpty())
                                param.description = getStructDescription(param.type);
                        }
                    }
                    structParams.add(param);
                    if (param.recursiveName == null
                        && (param.type.fixed == Apidoc.Type.OBJECT
                        || param.type.fixed == Apidoc.Type.ARRAY))
                    {
                        structParams.addAll(structToParams( //< Recursion.
                            name,
                            param.type,
                            paramDirection,
                            overriddenParams,
                            processedStructs));
                    }
                }
                type.mapValueType = null;
            }
            else if (type.mapValueType.fixed == Apidoc.Type.OBJECT
                || type.mapValueType.fixed == Apidoc.Type.ARRAY)
            {
                structParams.addAll(structToParams(
                    namePrefix + TypeInfo.mapKeyPlaceholder,
                    type.mapValueType,
                    paramDirection,
                    overriddenParams,
                    processedStructs));
            }
            return structParams;
        }

        if (type.name == null || TypeInfo.nullType.equals(type.name))
            return structParams;

        final StructParser.StructInfo structInfo = structInfo(type);
        if (structInfo == null)
            return structParams;

        List<Apidoc.Param> paramsFromItems;
        try
        {
            paramsFromItems = ApidocCommentParser.parseParams(
                structInfo.items,
                namePrefix,
                paramDirection,
                ApidocCommentParser.ParamMode.WithToken);
            overriddenParams.addAll(paramsFromItems);
        }
        catch (ApidocCommentParser.Error e)
        {
            throw new Error(e.getMessage());
        }
        processedStructs.put(structInfo.name, namePrefix);
        if (structInfo.isMap)
            namePrefix += TypeInfo.mapKeyPlaceholder + '.';
        List<Apidoc.Param> params = new ArrayList<>();
        for (final StructParser.StructInfo.Field field: structInfo.fields)
        {
            final String name = namePrefix + field.name;
            final Apidoc.Param overriddenParam = findParam(overriddenParams, name);
            if (overriddenParam != null && overriddenParam.unused)
                continue;

            Apidoc.Param param;
            try
            {
                param = ApidocCommentParser.parseParam(
                    field.items, paramDirection, ApidocCommentParser.ParamMode.WithoutToken);
            }
            catch (ApidocCommentParser.Error e)
            {
                throw new Error(e.getMessage());
            }

            if (param == null)
            {
                param = findParam(paramsFromItems, name);
                if (param == null)
                    param = new Apidoc.Param();
            }
            param.isGeneratedFromStruct = true;
            param.name = name;
            param.type.fillMissingType(field.type);
            if (field.type.isStdOptional)
                param.optional = true;
            if (param.type.name != null)
            {
                if (param.type.fixed == Apidoc.Type.ENUM || param.type.fixed == Apidoc.Type.FLAGS)
                {
                    enumToParam(param, param.type.name);
                }
                else
                {
                    param.recursiveName = processedStructs.get(param.type.name);
                    final StructParser.StructInfo fieldStructInfo = structs.get(param.type.name);
                    if (fieldStructInfo != null)
                        fieldStructInfo.fillParamAttributes(param);
                    if (param.description == null || param.description.isEmpty())
                        param.description = getStructDescription(param.type);
                }
            }
            if (overriddenParam != null)
            {
                overriddenParam.fillMissingFieldsFrom(param);
                params.add(overriddenParam);
            }
            else
            {
                params.add(param);
            }

            if (param.recursiveName == null
                && (param.type.fixed == Apidoc.Type.OBJECT
                    || param.type.fixed == Apidoc.Type.ARRAY
                    || param.type.variantValueTypes != null))
            {
                params.addAll(structToParams( //< Recursion.
                    name,
                    param.type,
                    paramDirection,
                    overriddenParams,
                    processedStructs));
            }
        }

        // Add all "fantom" fields - `items` which have no corresponding field in the struct
        // definition, but are mentioned in `items`. Such fields remain in overriddenParams.
        for (final Apidoc.Param paramFromItems: paramsFromItems)
        {
            if (findParam(params, paramFromItems.name) == null)
                params.add(paramFromItems);
        }

        // Preserve unused orderBy parameter if specified so we can omit orderBy
        // during json generation.
        for (final Apidoc.Param overwrittenParam: overriddenParams)
        {
            if (overwrittenParam.isUnusedOrderBy())
                params.add(overwrittenParam);
        }

        processedStructs.remove(structInfo.name);

        return params;
    }

    public void correctType(TypeInfo type)
    {
        if (type.mapValueType != null)
        {
            correctType(type.mapKeyType);
            correctType(type.mapValueType);
            if (type.fixed == Apidoc.Type.UNKNOWN)
                type.fixed = Apidoc.Type.OBJECT;
            return;
        }

        if (type.variantValueTypes != null)
        {
            for (final TypeInfo variantType: type.variantValueTypes)
                correctType(variantType);
            if (type.fixed == Apidoc.Type.UNKNOWN)
                type.fixed = Apidoc.Type.OBJECT;
            return;
        }

        if (type.name == null)
            return;

        assert !type.name.isEmpty();

        if (type.fixed != Apidoc.Type.UNKNOWN && type.fixed != Apidoc.Type.ARRAY)
            return;

        FlagParser.FlagInfo flag = flags.get(type.name);
        if (flag != null)
        {
            type.fixed =
                (type.fixed == Apidoc.Type.ARRAY) ? Apidoc.Type.STRING_ARRAY : Apidoc.Type.FLAGS;
            type.name = flag.enumName;
        }
        else if (enums.get(type.name) != null)
        {
            type.fixed =
                (type.fixed == Apidoc.Type.ARRAY) ? Apidoc.Type.STRING_ARRAY : Apidoc.Type.ENUM;
        }
        else if (structs.get(type.name) != null)
        {
            if (type.fixed == Apidoc.Type.UNKNOWN)
                type.fixed = Apidoc.Type.OBJECT;
        }
    }

    private void correctTypes() throws Error
    {
        for (StructParser.StructInfo struct: structs.values())
        {
            for (StructParser.StructInfo.Field field: struct.fields)
            {
                correctType(field.type);
            }
        }
    }

    private void makeStructsFlat() throws Error
    {
        for (StructParser.StructInfo struct: structs.values())
        {
            if (struct.baseTypeNames != null)
            {
                List<ApidocTagParser.Item> items = new ArrayList<ApidocTagParser.Item>();
                makeStructFlat(struct.fields, items, struct);
                if (!items.isEmpty())
                {
                    if (struct.items == null)
                        struct.items = items;
                    else
                        struct.items.addAll(items);
                }
                struct.baseTypeNames.clear();
            }
        }
    }

    private void makeStructFlat(
        List<StructParser.StructInfo.Field> fields,
        List<ApidocTagParser.Item> items,
        StructParser.StructInfo struct)
        throws Error
    {
        if (struct.items != null && !struct.items.isEmpty())
        {
            final ApidocTagParser.Item item = struct.items.get(0);
            if (ApidocComment.TAG_APIDOC.equals(item.getTag()))
            {
                final String label = struct.items.get(0).getLabel();
                if (label != null && !label.isEmpty())
                {
                    TypeInfo type = new TypeInfo();
                    try
                    {
                        type.fillFromLabel(label);
                    }
                    catch (Exception e)
                    {
                        throw new Error(item.getErrorPrefix() + "Invalid overridden type \"" +
                            label + "\" for struct \"" + struct.name + "\" found: " +
                            e.getMessage() + ".");
                    }
                    if (!type.isParsed())
                    {
                        StructParser.StructInfo overridden = structOrMapInfo(type);
                        if (overridden != null)
                        {
                            fields.addAll(0, overridden.fields);
                            if (overridden.items != null)
                                items.addAll(overridden.items);
                        }
                    }
                    return;
                }
            }
        }

        ListIterator<String> it = struct.baseTypeNames.listIterator(struct.baseTypeNames.size());
        while (it.hasPrevious())
        {
            TypeInfo type = new TypeInfo();
            try
            {
                type.fillFromName(it.previous());
            }
            catch (Exception e)
            {
                throw new Error(e.getMessage());
            }
            StructParser.StructInfo baseStruct = structOrMapInfo(type);
            if (baseStruct == null)
            {
                throw new Error(
                    "Base structure `" + type.name + "` of `" + struct.name + "` not " + "found.");
            }
            fields.addAll(0, baseStruct.fields);
            if (baseStruct.items != null)
                items.addAll(baseStruct.items);
            if (baseStruct.baseTypeNames != null)
                makeStructFlat(fields, items, baseStruct);
        }
    }

    private void enumToParam(Apidoc.Param param, String enumName)
        throws Error
    {
        EnumParser.EnumInfo enumInfo = enums.get(enumName);
        if (enumInfo == null)
            return;

        if (param.description == null || param.description.isEmpty())
            param.description = enumInfo.description;

        for (EnumParser.EnumInfo.Value enumValue: enumInfo.values)
        {
            Apidoc.Value value = findValue(param.values, enumValue.name);
            if (value == null)
            {
                value = new Apidoc.Value();
                value.name = enumValue.name;
                value.description = enumValue.description;
                value.unused = enumValue.unused;
                value.proprietary = enumValue.proprietary;
                value.deprecated = enumValue.deprecated;
                value.deprecatedDescription = enumValue.deprecatedDescription;
                param.values.add(value);
            }
        }
    }

    private static Apidoc.Value findValue(List<Apidoc.Value> values, String name)
    {
        for (Apidoc.Value value: values)
        {
            if (value.name.equals(name))
                return value;
        }
        return null;
    }

    private static Apidoc.Param findParam(List<Apidoc.Param> params, String name)
    {
        if (params == null)
            return null;

        for (Apidoc.Param param: params)
        {
            if (param.name.equals(name))
                return param;
        }
        return null;
    }

    private final boolean verbose;
    private final Map<String, EnumParser.EnumInfo> enums =
        new HashMap<String, EnumParser.EnumInfo>();
    private final Map<String, FlagParser.FlagInfo> flags =
        new HashMap<String, FlagParser.FlagInfo>();
    private final Map<String, StructParser.StructInfo> structs =
        new HashMap<String, StructParser.StructInfo>();
}
