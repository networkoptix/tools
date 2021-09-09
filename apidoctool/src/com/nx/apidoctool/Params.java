package com.nx.apidoctool;

import com.nx.util.ParamsBase;

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
        "Produce an error if a parameter type is unspecified and cannot be deduced from the " +
            "struct field.");

    public boolean generateOrderByParameters() throws Exception
    {
        return toBoolean(generateOrderByParameters, "generateOrderByParameters");
    }

    private final StringBuilder generateOrderByParameters = regStringParam(
        "generateOrderByParameters",
        "false",
        "Whether the default query parameter `_orderBy` must be generated to sort response lists " +
            "by their fields.");

    public int requiredFunctionCaptionLenLimit() throws Exception
    {
        return toUnsignedInt(
            requiredFunctionCaptionLenLimit, "requiredFunctionCaptionLenLimit", -1);
    }

    private final StringBuilder requiredFunctionCaptionLenLimit = regStringParam(
        "requiredFunctionCaptionLenLimit",
        "",
        "Produce an error if there is no `caption` tag for the API function, or it is longer " +
            "than this specified limit. Specify 0 to require unlimited captions.");

    public int requiredGroupNameLenLimit() throws Exception
    {
        return toUnsignedInt(requiredGroupNameLenLimit, "requiredGroupNameLenLimit", -1);
    }

    private final StringBuilder requiredGroupNameLenLimit = regStringParam(
        "requiredGroupNameLenLimit",
        "",
        "Produce an error if there is no `group` tag for the API function, or its name is " +
            "longer than this specified limit. Specify 0 to require unlimited names.");

    public String templateRegistrationCpp() { return templateRegistrationCpp.toString(); }

    private final StringBuilder templateRegistrationCpp = regStringParam("templateRegistrationCpp",
        "",
        "A cpp file where \"template\" API functions are registered.");

    public String handlerRegistrationCpp() { return handlerRegistrationCpp.toString(); }

    private final StringBuilder handlerRegistrationCpp = regStringParam("handlerRegistrationCpp",
        "",
        "A comma-separated list of cpp files where \"handler\" API functions are registered.");

    public String functionCommentSources() { return functionCommentSources.toString(); }

    private final StringBuilder functionCommentSources = regStringParam("functionCommentSources",
        "",
        "A comma-separated list of source files with apidoc comments for API functions.");

    public String typeHeaderPaths() { return typeHeaderPaths.toString(); }

    private final StringBuilder typeHeaderPaths = regStringParam("typeHeaderPaths",
        "",
        "A comma-separated list of dirs and/or .h files where C++ types are defined.");

    public String urlPrefixReplacement() { return urlPrefixReplacement.toString(); }

    private final StringBuilder urlPrefixReplacement = regStringParam("urlPrefixReplacement",
        "",
        "A comma-separated list of API function URL prefix replacement string pairs, if\n" +
        "specified. Each string replacement pair must be separated by space. The first part is\n" +
        "the target, the second part is the replacement.");

    private static boolean toBoolean(StringBuilder param, String paramName) throws Exception
    {
        final String value = param.toString().trim();
        if (value.equalsIgnoreCase("true") || value.equals("1"))
            return true;
        if (value.equalsIgnoreCase("false") || value.equals("0"))
            return false;
        throw new Exception("Param \"" + paramName + "\" must be true, 1, false or 0.");
    }

    private static int toUnsignedInt(StringBuilder param, String paramName, int emptyValue)
        throws Exception
    {
        final String value = param.toString().trim();
        if (value.isEmpty())
            return emptyValue;
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
