package com.nx.apidoctool;

import com.nx.util.ParamsBase;

/**
 * Parameters that allow apidoctool to find necessary places in C++ code: file names, etc.
 */
public class Params
    extends ParamsBase
{
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
