package com.nx.apidoc;

import com.nx.util.SourceCode;

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

    public TypeManager(
        boolean verbose, boolean invalidChronoFieldSuffixIsError, boolean unknownParamTypeIsError)
    {
        this.verbose = verbose;
        this.invalidChronoFieldSuffixIsError = invalidChronoFieldSuffixIsError;
        this.unknownParamTypeIsError = unknownParamTypeIsError;
    }

    public TypeManager(boolean verbose)
    {
        this(verbose, /*invalidChronoFieldSuffixIsError*/ false, /*unknownParamTypeIsError*/ false);
    }

    public final void processFiles(List<File> files)
        throws Error, IOException, EnumParser.Error, SourceCode.Error, ApidocTagParser.Error,
            FlagParser.Error, StructParser.Error
    {
        for (File file: files)
        {
            final SourceCode sourceCode = new SourceCode(file);

            final EnumParser enumParser = new EnumParser(sourceCode, verbose);
            enums.putAll(enumParser.parseEnums());

            final FlagParser flagParser = new FlagParser(sourceCode, verbose);
            flags.putAll(flagParser.parseFlags());

            final StructParser structParser =
                new StructParser(sourceCode, verbose, invalidChronoFieldSuffixIsError);
            structs.putAll(structParser.parseStructs());
        }
        makeStructsFlat();
        fillUnknownTypes();
    }

    public final void mergeDescription(
        String inputDataType, String outputDataType, Apidoc.Function function)
        throws Error
    {
        if (outputDataType != null)
        {
            // TODO: #lbusygin: Add parsing of typedefs to move apidoc near declaration to avoid
            // duplicate description.
            if (outputDataType.endsWith("List"))
            {
                function.result.type = Apidoc.Type.ARRAY;
                outputDataType = outputDataType.substring(
                    0, outputDataType.length() - "List".length());
            }
            else if (!outputDataType.isEmpty())
            {
                if (function.result.type == Apidoc.Type.UNKNOWN)
                    function.result.type = Apidoc.Type.OBJECT;
            }
            function.result.params = mergeStructParams(
                outputDataType,
                function.result.params,
                function.result.unusedParams,
                ApidocCommentParser.ParamDirection.Input);
            if (function.result.caption.isEmpty())
            {
                // Take the function result caption from the output struct description.
                final StructParser.StructInfo structInfo = structs.get(outputDataType);
                if (structInfo != null)
                    function.result.caption = structInfo.description();
            }
        }

        if (inputDataType != null)
        {
            if (inputDataType.endsWith("List"))
            {
                inputDataType = inputDataType.substring(
                    0, inputDataType.length() - "List".length());
            }
            function.input.params = mergeStructParams(
                inputDataType,
                function.input.params,
                function.input.unusedParams,
                ApidocCommentParser.ParamDirection.Input);
        }
    }

    public List<Apidoc.Param> getStructParams(
        String structName, String prefix, ApidocCommentParser.ParamDirection paramDirection)
        throws Error
    {
        StructParser.StructInfo structInfo = structs.get(structName);
        if (structInfo == null)
        {
            if (unknownParamTypeIsError)
                throw new Error("Struct `" + structName + "` not found.");
            System.out.println("WARNING: Struct `" + structName + "` not found.");
            return null;
        }
        return structToParams(prefix, structInfo, paramDirection, new ArrayList<Apidoc.Param>(), new ArrayList<String>());
    }

    /**
     * @return Empty string if the struct was not found, or has no description.
     */
    public String getStructDescription(String structName)
        throws Error
    {
        StructParser.StructInfo structInfo = structs.get(structName);
        if (structInfo == null)
        {
            if (unknownParamTypeIsError)
                throw new Error("Struct `" + structName + "` not found.");
            System.out.println("WARNING: Struct `" + structName + "` not found.");
            return "";
        }
        return structInfo.description();
    }

    private List<Apidoc.Param> mergeStructParams(
        String structName,
        List<Apidoc.Param> functionParams,
        List<Apidoc.Param> unusedParams,
        ApidocCommentParser.ParamDirection paramDirection)
        throws Error
    {
        if (structName.equals("") || structName.equals("nullptr_t"))
            return functionParams;

        final StructParser.StructInfo structInfo = structs.get(structName);
        if (structInfo == null)
        {
            if (structName.equals("QnUuid"))
            {
                final Apidoc.Param functionParam = findParam(functionParams, "id");
                if (functionParam != null)
                    functionParam.type = Apidoc.Type.UUID;
            }
            else
            {
                if (unknownParamTypeIsError)
                    throw new Error("Struct `" + structName + "` not found.");
                System.out.println("WARNING: Struct `" + structName + "` not found.");
            }
            return functionParams;
        }

        final List<Apidoc.Param> structParams = structToParams(
            /*namePrefix*/ "", structInfo, paramDirection, new ArrayList<Apidoc.Param>(), new ArrayList<String>());
        final List<Apidoc.Param> mergedParams = new ArrayList<Apidoc.Param>();
        for (Apidoc.Param structParam: structParams)
        {
            if (structParam.unused)
                continue;
            if (findParam(unusedParams, structParam.name) != null) //< Skip unused params.
                continue;
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

            if (structParam.type == Apidoc.Type.UNKNOWN
                && functionParam != null
                && functionParam.type == Apidoc.Type.UNKNOWN
                && !structParam.hasDefaultDescription)
            {
                throw new Error("Param type not found: \"" + structParam.name
                    + "\" in struct \"" + structName + "\"");
            }
            if (functionParam != null)
            {
                functionParam.fillMissingFieldsFrom(structParam);
                functionParam.normalizeProperties();

                mergedParams.add(functionParam);
                if (functionParam.type == Apidoc.Type.OBJECT_JSON
                    || functionParam.type == Apidoc.Type.ARRAY_JSON)
                {
                    final boolean isArray = functionParam.type == Apidoc.Type.ARRAY_JSON;
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
                if (verbose)
                {
                    System.out.println(
                        "            WARNING: Param in function apidoc comment: \"" + param.name
                            + "\" not found in structure: " + structName);
                }
                mergedParams.add(param);
            }
        }
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
        StructParser.StructInfo structInfo,
        ApidocCommentParser.ParamDirection paramDirection,
        List<Apidoc.Param> overriddenParams,
        List<String> processedStructs)
        throws Error
    {
        processedStructs.add(structInfo.name);

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
        List<Apidoc.Param> params = new ArrayList<Apidoc.Param>();
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
                param = new Apidoc.Param();

            param.structName = structInfo.name;
            param.isGeneratedFromStruct = true;

            param.name = name;
            if (field.type == Apidoc.Type.ENUM || field.type == Apidoc.Type.FLAGS)
                enumToParam(param, field.typeName);

            final boolean isTypeAlreadyProcessed = field.typeName != null
                && processedStructs.contains(field.typeName);
            if (param.type == null || param.type == Apidoc.Type.UNKNOWN)
                param.type = field.type;
            if (field.isStdOptional)
                param.optional = true;
            if (isTypeAlreadyProcessed)
                param.hasRecursiveField = true;

            if (overriddenParam != null)
            {
                overriddenParam.fillMissingFieldsFrom(param);
                params.add(overriddenParam);
            }
            else
            {
                params.add(param);
            }

            if (!isTypeAlreadyProcessed && (field.type == Apidoc.Type.OBJECT || field.type == Apidoc.Type.ARRAY))
            {
                StructParser.StructInfo innerStructInfo = structs.get(field.typeName);
                if (innerStructInfo == null)
                    throw new Error("Struct \"" + field.typeName + "\" not found");

                if (param.description == null || param.description.isEmpty())
                    param.description = innerStructInfo.description();

                String nextNamePrefix = param.name;
                if (field.type == Apidoc.Type.ARRAY)
                    nextNamePrefix += "[].";
                else
                    nextNamePrefix += ".";

                params.addAll(
                    structToParams( //< Recursion.
                        nextNamePrefix, innerStructInfo, paramDirection, overriddenParams, processedStructs));
            }
        }

        // Add all "fantom" fields - `items` which have no corresponding field in the struct
        // definition, but are mentioned in `items`. Such fields remain in overriddenParams.
        for (final Apidoc.Param paramFromItems: paramsFromItems)
        {
            if (findParam(params, paramFromItems.name) == null)
                params.add(paramFromItems);
        }

        processedStructs.remove(processedStructs.size() - 1);

        return params;
    }

    private void fillUnknownTypes()
    {
        for (StructParser.StructInfo struct: structs.values())
        {
            for (StructParser.StructInfo.Field field: struct.fields)
            {
                if (field.type == Apidoc.Type.UNKNOWN)
                {
                    FlagParser.FlagInfo flag = flags.get(field.typeName);
                    if (flag != null)
                    {
                        field.type = Apidoc.Type.FLAGS;
                        field.typeName = flag.enumName;
                    }
                    else if (enums.get(field.typeName) != null)
                    {
                        field.type = Apidoc.Type.ENUM;
                    }
                    else if (structs.get(field.typeName) != null)
                    {
                        field.type = Apidoc.Type.OBJECT;
                    }
                }
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
                makeStructFlat(struct.fields, items, struct.baseTypeNames);
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
        List<String> baseTypeNames)
        throws Error
    {
        ListIterator<String> it = baseTypeNames.listIterator(baseTypeNames.size());
        while (it.hasPrevious())
        {
            final String baseTypeName = it.previous();
            StructParser.StructInfo baseStruct = structs.get(baseTypeName);
            if (baseStruct == null)
                throw new Error("Base structure not found: \"" + baseTypeName + "\"");

            fields.addAll(0, baseStruct.fields);
            if (baseStruct.items != null)
                items.addAll(baseStruct.items);
            if (baseStruct.baseTypeNames != null)
                makeStructFlat(fields, items, baseStruct.baseTypeNames);
        }
    }

    private void enumToParam(Apidoc.Param param, String enumName)
        throws Error
    {
        EnumParser.EnumInfo enumInfo = enums.get(enumName);
        if (enumInfo == null)
            throw new Error("Enum \"" + enumName + "\" not found");

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
    private final boolean invalidChronoFieldSuffixIsError;
    private final boolean unknownParamTypeIsError;

    private final Map<String, EnumParser.EnumInfo> enums =
        new HashMap<String, EnumParser.EnumInfo>();
    private final Map<String, FlagParser.FlagInfo> flags =
        new HashMap<String, FlagParser.FlagInfo>();
    private final Map<String, StructParser.StructInfo> structs =
        new HashMap<String, StructParser.StructInfo>();
}
