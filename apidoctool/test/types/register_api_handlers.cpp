    /**%apidoc:{ExampleData} POST /rest/v2/example/{name}
     * %param:string name
     * %param:string funcParam
     * %param inner.i description
     * %param variant.#1.i description
     * %param variantWithMap.#1.*.i description
     * %param variantWithList.#1[].i description
     * %param variantWithMapList.#1[].*.i description
     * %param map.*.i description
     * %param mapList[].*.i description
     * %param mapOfList.*[].i description
     * %param mapOfNamedMap.*.i description
     * %ingroup Test
     * %return:{ExampleData}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/secondS
     * %ingroup Test
     * %return:{std::chrono::seconds}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/secondListS
     * %ingroup Test
     * %return:{std::vector<std::chrono::seconds>}
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
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/mapList
     * %ingroup Test
     * %return:{std::vector<std::map<QString, ExampleStruct>>}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/mapOfList
     * %ingroup Test
     * %return:{std::map<QString, std::vector<ExampleStruct>>}
     */
    reg("example", GlobalPermission::admin);

    /**%apidoc GET /rest/v2/example/mapOfNamedMap
     * %ingroup Test
     * %return:{std::map<QString, NamedMap>}
     */
    reg("example", GlobalPermission::admin);
