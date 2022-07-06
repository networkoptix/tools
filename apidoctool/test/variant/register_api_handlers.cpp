    /**%apidoc POST /jsonrpc
     * %caption Single endpoint API interface
     * %ingroup JSON-RPC
     * %struct JsonRpcRequest
     * %permissions Depends on resource access rights.
     * %return:{JsonRpcResponse}
     *
     **%apidoc OPTIONS /jsonrpc
     * %caption Web socket API interface
     * %ingroup JSON-RPC
     * %permissions Depends on resource access rights.
     * %return Response with `switching protocols` HTTP status code.
     */
    reg("jsonrpc",
        GlobalPermission::none,
        std::make_unique<JsonRpcHandler>(serverModule->commonModule(), processorPool),
        nx::network::http::Method::post);
