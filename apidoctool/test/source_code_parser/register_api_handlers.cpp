
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
