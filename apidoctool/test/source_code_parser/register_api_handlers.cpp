
    /**%apidoc GET /api/testHandler
     * Test GET handler's description.
     * %param:string String param's description".
     * %return
     *     %struct StructC
     *
     * %apidoc POST /api/testHandler
     * Test POST handler's description
     * %struct StructF
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
