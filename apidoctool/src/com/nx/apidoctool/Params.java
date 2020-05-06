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
        "A cpp file where \"template\" methods are registered.");

    public String handlerRegistrationCpp() { return handlerRegistrationCpp.toString(); }
    private final StringBuilder handlerRegistrationCpp = regStringParam("handlerRegistrationCpp",
            "/mediaserver_core/src/media_server_process.cpp",
            "A cpp file where \"handler\" methods are registered.");

    public String typeHeaderPaths() { return typeHeaderPaths.toString(); }
    private final StringBuilder typeHeaderPaths = regStringParam("typeHeaderPaths",
        "",
        "A comma-separated list of dirs and/or .h files where C++ types are defined.");

    public String urlPrefixReplacement() { return urlPrefixReplacement.toString(); }
    private final StringBuilder urlPrefixReplacement = regStringParam("urlPrefixReplacement",
        "",
        "The method URL prefix replacement string pair if specified. " +
            "The first string is the target, the second string is the replacement.");
}
