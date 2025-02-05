// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

package com.nx.apidoctool;

import com.nx.utils.ParamsBase;

/**
 * Parameters that allow apidoctool to find necessary places in C++ code: file names, etc.
 */
public class Params
    extends ParamsBase
{
    public boolean invalidChronoFieldSuffixIsError() throws Exception
    {
        return toBoolean(invalidChronoFieldSuffixIsError, "invalidChronoFieldSuffixIsError");
    }

    private final StringBuilder invalidChronoFieldSuffixIsError = regStringParam(
        "invalidChronoFieldSuffixIsError",
        "false",
"If true, produce an error on invalid measurement unit suffix of `std::chrono` type field.");

    public boolean unknownParamTypeIsError() throws Exception
    {
        return toBoolean(unknownParamTypeIsError, "unknownParamTypeIsError");
    }

    private final StringBuilder unknownParamTypeIsError = regStringParam(
        "unknownParamTypeIsError",
        "false",
"Produce an error if a parameter type is unspecified and cannot be deduced from the struct\n" +
"field.");

    public boolean responseChronoAsString() throws Exception
    {
        return toBoolean(responseChronoAsString, "responseChronoAsString");
    }

    private final StringBuilder responseChronoAsString = regStringParam(
        "responseChronoAsString",
        "true",
"If true, then the type of the response chrono fields is string otherwise integer.");

    public boolean generateOrderByParameters() throws Exception
    {
        return toBoolean(generateOrderByParameters, "generateOrderByParameters");
    }

    private final StringBuilder generateOrderByParameters = regStringParam(
        "generateOrderByParameters",
        "false",
"Whether the default query parameter `_orderBy` must be generated to sort response lists by\n" +
"their fields.");

    public boolean jsonrpc() throws Exception
    {
        return toBoolean(jsonrpc, "jsonrpc");
    }

    private final StringBuilder jsonrpc = regStringParam(
        "jsonrpc",
        "false",
"Whether %jsonrpc tags must be processed and jsonrpc extensions generated for each function.");

    public int requiredFunctionCaptionLenLimit() throws Exception
    {
        return toNonNegativeInt(
            requiredFunctionCaptionLenLimit, "requiredFunctionCaptionLenLimit", -1);
    }

    private final StringBuilder requiredFunctionCaptionLenLimit = regStringParam(
        "requiredFunctionCaptionLenLimit",
        "",
"Produce an error if there is no `caption` tag for the API function, or it is longer than this\n" +
"specified limit. Specify 0 to require unlimited captions.");

    public int requiredGroupNameLenLimit() throws Exception
    {
        return toNonNegativeInt(requiredGroupNameLenLimit, "requiredGroupNameLenLimit", -1);
    }

    private final StringBuilder requiredGroupNameLenLimit = regStringParam(
        "requiredGroupNameLenLimit",
        "",
"Produce an error if there is no `group` tag for the API function, or its name is longer than\n" +
"this specified limit. Specify 0 to require unlimited names.");

    public String templateRegistrationCpp() { return templateRegistrationCpp.toString(); }

    private final StringBuilder templateRegistrationCpp = regStringParam("templateRegistrationCpp",
        "",
"A cpp file where \"template\" API functions are registered.");

    public String handlerRegistrationCpp() { return handlerRegistrationCpp.toString(); }

    private final StringBuilder handlerRegistrationCpp = regStringParam("handlerRegistrationCpp",
        "",
"A comma-separated list of cpp files where \"handler\" API functions are registered.");

    public String functionCommentSources() { return functionCommentSources.toString(); }

    public String transactionBusSources() { return transactionBusSources.toString(); }

    private final StringBuilder functionCommentSources = regStringParam("functionCommentSources",
        "",
"A comma-separated list of source files with apidoc comments for API functions.");

    private final StringBuilder transactionBusSources = regStringParam("transactionBusSources",
        "",
"A comma-separated list of source files with apidoc comments for Transaction Bus transactions.");

    public String typeHeaderPaths() { return typeHeaderPaths.toString(); }

    public boolean enableEnumValueMerge() throws Exception
    {
        return toBoolean(enableEnumValueMerge, "enableEnumValueMerge");
    }

    private final StringBuilder enableEnumValueMerge = regStringParam(
        "enableEnumValueMerge",
        "false",
"Merge enum values listed under the %value tag in a function comment with enum values that\n" +
"were found during parsing of a struct field comment or an enum comment");

    private final StringBuilder typeHeaderPaths = regStringParam("typeHeaderPaths",
        "",
"A comma-separated list of dirs and/or .h files where C++ types are defined.");

    public String urlPrefixReplacement() { return urlPrefixReplacement.toString(); }

    private final StringBuilder urlPrefixReplacement = regStringParam("urlPrefixReplacement",
        "",
"A comma-separated list of space-separated string pairs; each pair contains the target and the\n" +
"replacement string to be applied to each API function URLs. The target will match only if a\n" +
"slash appears before and after it.");

    public String apiVersions() { return apiVersions.toString(); }

    private final StringBuilder apiVersions = regStringParam("apiVersions",
        "",
"A comma-separated list of prefixes with API versions like `/rest/v2`.");

    private static boolean toBoolean(StringBuilder param, String paramName) throws Exception
    {
        final String value = param.toString().trim();
        if (value.equalsIgnoreCase("true") || value.equals("1"))
            return true;
        if (value.equalsIgnoreCase("false") || value.equals("0"))
            return false;
        throw new Exception("Param \"" + paramName + "\" must be true, 1, false or 0.");
    }

    private static int toNonNegativeInt(StringBuilder param, String paramName, int defaultValue)
        throws Exception
    {
        final String value = param.toString().trim();
        if (value.isEmpty())
            return defaultValue;
        try
        {
            final int result = Integer.parseInt(value);
            if (result >= 0)
                return result;
        }
        catch (NumberFormatException e)
        {
        }
        throw new Exception("Param \"" + paramName + "\" must be a non-negative integer.");
    }
}
