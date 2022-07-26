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
