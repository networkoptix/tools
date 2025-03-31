// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

    /**%apidoc:{ExampleData} POST /rest/v2/example/{name}
     * Function with deprecated &ast;.
     * %deprecated Deprecated function &ast;.
     * %param:string name
     *     %example Example param
     * %param:string funcParam
     * %param inner.i description
     *     %example 1
     * %param variant.#1.i description
     * %param variantOfTwoStructs.#0.i description
     * %param variantOfTwoStructs.#1.i description
     * %param variantList[].#1.i description
     * %param variantWithMap.#1.*.i description
     * %param variantWithList.#1[].i description
     * %param variantWithMapList.#1[].*.i description
     * %param variantWithVariant.#1.#1.i description
     * %param map.*.i description
     * %param mapList[].*.i description
     * %param mapOfList.*[].i description
     * %param mapOfNamedMap.*.*.i description
     * %param mapWithVariant.*.#1.i description
     * %param mapListWithVariant[].*.#1.i description
     * %param mapWithVariantList.*[].#1.i description
     * %param mapOfMap.*.*.i description
     * %param mapOfMapWithVariant.*.*.#1.i description
     * %ingroup Test
     * %return:{ExampleData}
     *     Function response &ast;.
     *     %param inner.i description
     *     %param variant.#1.i description
     *     %param variantOfTwoStructs.#0.i description
     *     %param variantOfTwoStructs.#1.i description
     *     %param variantList[].#1.i description
     *     %param variantWithMap.#1.*.i description
     *     %param variantWithList.#1[].i description
     *     %param variantWithMapList.#1[].*.i description
     *     %param variantWithVariant.#1.#1.i description
     *     %param map.*.i description
     *     %param mapList[].*.i description
     *     %param mapOfList.*[].i description
     *     %param mapOfNamedMap.*.*.i description
     *     %param mapWithVariant.*.#1.i description
     *     %param mapListWithVariant[].*.#1.i description
     *     %param mapWithVariantList.*[].#1.i description
     *     %param mapOfMap.*.*.i description
     *     %param mapOfMapWithVariant.*.*.#1.i description
     *
     **%apidoc:{ExampleData} GET /rest/v2/example/{name}
     * %param:string name
     *     %example Example param
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc:{EnumOrderByExampleData} GET /rest/v2/example/enumOrderBy
     * %return:{EnumOrderByExampleData}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc:{StringOrderByExampleData} GET /rest/v2/example/stringOrderBy
     * %return:{StringOrderByExampleData}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc:{ExampleData} GET /rest/v2/example/paramOrderBy
     * %param:string _orderBy
     * %value id
     * %value name
     * %return:{StringOrderByExampleData}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc:{ExampleData} GET /rest/v2/example/unusedOrderBy
     * %param[unused] _orderBy
     * %return:{StructSeconds}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc:{StructSeconds} GET /rest/v2/example/secondS
     * %ingroup Test
     * %return:{std::chrono::seconds}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/secondListS
     * %ingroup Test
     * %return:{std::vector<std::chrono::seconds>}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/variant
     * %ingroup Test
     * %return:{std::variant<int, ExampleStruct>}
     *     %param #1.i description
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/variantOfTwoStructs
     * %ingroup Test
     * %return:{std::variant<ExampleStruct, ExampleStruct>}
     *     %param #0.i description
     *     %param #1.i description
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/variantList
     * %ingroup Test
     * %return:{std::vector<std::variant<int, ExampleStruct>>}
     *     %param #1.i description
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/variantWithChrono
     * %ingroup Test
     * %return:{std::variant<int, std::chrono::seconds>}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/map
     * %ingroup Test
     * %return:{std::map<QString, ExampleStruct>}
     *     %param *.i description
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/mapList
     * %ingroup Test
     * %return:{std::vector<std::map<QString, ExampleStruct>>}
     *     %param *.i description
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/mapOfList
     * %ingroup Test
     * %return:{std::map<QString, std::vector<ExampleStruct>>}
     *     %param *[].i description
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/mapOfNamedMap
     * %ingroup Test
     * %return:{std::map<QString, NamedMap>}
     *     %param *.*.i description
     */
    reg("example", GlobalPermission::admin);
