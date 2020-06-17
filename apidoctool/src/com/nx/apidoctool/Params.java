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
        final String value = invalidChronoFieldSuffixIsError.toString().trim();
        if (value.equalsIgnoreCase("true") || value.equals("1"))
            return true;
        if (value.equalsIgnoreCase("false") || value.equals("0"))
            return false;
        throw new Exception(
            "Param \"invalidChronoFieldSuffixIsError\" must be true, 1, false or 0.");
    }

    private final StringBuilder invalidChronoFieldSuffixIsError = regStringParam(
        "invalidChronoFieldSuffixIsError",
        "false",
        "If true, produce an error on invalid measurement unit suffix of `std::chrono` type field.");

    public boolean unknownParamTypeIsError()
    {
        final String value = unknownParamTypeIsError.toString().trim();
        return !value.equalsIgnoreCase("false") && !value.equals("0");
    }

    private final StringBuilder unknownParamTypeIsError = regStringParam(
        "unknownParamTypeIsError",
        "false",
        "Produce an error if a parameter type is unspecified and cannot be deduced from the " +
            "struct field.");

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
}
