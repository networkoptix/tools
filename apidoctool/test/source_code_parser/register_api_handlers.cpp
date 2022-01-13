
    /**%apidoc GET /api/testHandler
     * Test GET handler's description.
     * %param:string String param's description".
     * %return
     *     %struct StructC
     *
     * %apidoc POST /api/testHandler
     * Test POST handler's description
     * %struct StructF
     * %param[ref] _format
     * %return:string
     */
    reg("api/testHandler", new testHandler());

    /**%apidoc GET /api/testHandler2
     * testHandler2 GET response description
     * %param:string analyticsEngineId Id of an Analytics Engine.
     * %return
     *     %struct Result
     *     %param[opt]:object reply Object with Engine settings model and values.
     *         %struct EngineSettingsResponse
     *
     **%apidoc POST /api/testHandler2
     * testHandler2 POST description
     * %struct EngineSettingsRequest
     * %return
     *     %struct Result
     *     %param[opt]:object reply Object with Engine settings model and values that the Engine
     *         returns after the values have been supplied.
     *         %struct EngineSettingsResponse
     */
    reg("api/testHandler2", new testHandler2());

    /**%apidoc GET /api/testHandler3
     * testHandler3 GET description
     * %return
     *     %struct Result
     *     %param partiallyDeprecatedTest Test that a partially deprecated enum param becomes fully
     *         deprecated.
     *         %value test7 Overridden value from an inherited enum.
     *             %deprecated
     */
    reg("api/testHandler3", new testHandler3());

    /**%apidoc GET /api/testHandler4
     * testHandler4 GET description
     * %return
     *     %struct Result
     *     %param partiallyProprietaryTest Test that one of the enum values becomes deprecated.
     *         %value[proprietary] test4 Overridden value from an inherited enum.
     */
    reg("api/testHandler4", new testHandler4());

    /**%apidoc GET /api/testHandler5
     * testHandler5 GET description
     * %return
     *     %struct Result
     *     %param:enum inPlaceEnum Test in-place enum.
     *         %value value0 Value description
     *         %value[proprietary] value1 Value description
     *         %value value2 Value description
     *             %deprecated
     */
    reg("api/testHandler5", new testHandler5());

    /**%apidoc GET /api/testHandler6
     * testHandler6 GET description
     * %return
     *     %struct Result
     *     %param errorString Test enumerating values for a non-enum type.
     *         %value val0 Value description
     *         %value val1 Value description
     *         %value val2 Value description
     */
    reg("api/testHandler6", new testHandler6());

    /**%apidoc:any POST /api/handlerWithType/{id}
     * handlerWithType POST description
     * %param:string id Id in path of handlerWithType.
     *
     **%apidoc[opt]:uuid PUT /api/handlerWithType/{id}
     * handlerWithType PUT description
     * %param:string id Id in path of handlerWithType.
     *
     **%apidoc:object PATCH /api/handlerWithType
     * handlerWithType PATCH description
     */
    reg("api/handlerWithType", new handlerWithType());
