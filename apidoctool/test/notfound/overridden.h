// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

struct KnownStruct
{
    int field;
};

struct NotFoundField
{
    NotFound notFoundField;
};

/**%apidoc
 * %param:{std::variant<std::nullptr_t, KnownStruct>} notFoundField
 */
struct NotFoundOverriddenParentField: NotFoundField
{
};

/**%apidoc:{QJsonObject} */
struct NotFoundOverriddenRequest: NotFound
{
    NotFoundOverriddenParentField field;
};

struct NotFoundOverriddenResponse
{
    NotFoundOverriddenParentField notFoundParentField;

    /**%apidoc:{KnownStruct} */
    NotFound::type notFoundObjectField;

    /**%apidoc:{std::variant<std::nullptr_t, KnownStruct>} */
    NotFound::type notFoundVariantField;

    /**%apidoc:string */
    NotFound notFoundStringField;

    NotFound notFoundFieldOverriddenInFunction;
};
