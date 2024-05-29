// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

    /**%apidoc POST /rest/test
     * %struct NotFoundOverriddenRequest
     * %ingroup Test
     * %return:{NotFoundOverriddenResponse}
     * %param:{std::variant<std::nullptr_t, KnownStruct>} notFoundFieldOverriddenInFunction
     */
    reg("test", GlobalPermission::admin);
