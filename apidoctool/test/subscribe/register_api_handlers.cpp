// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

    /**%apidoc GET /rest/test
     * %return:array
     *
     **%apidoc GET /rest/test/{id}
     * %param id
     * %return:object
     *
     **%apidoc POST /rest/test/{id}
     * %param id
     * %return:object
     *
     **%apidoc PUT /rest/test/{id}
     * %param id
     * %return:object
     *
     **%apidoc PATCH /rest/test/{id}
     * %param id
     * %return:object
     *
     **%apidoc DELETE /rest/test/{id}
     * %param id
     *
     **%apidoc GET /rest/test/{id}/afterId
     * %param id
     * %return:object
     *
     **%apidoc GET /rest/test/%2A/asterisk/{id}
     * %param id
     * %return:object
     *
     **%apidoc GET /rest/test/%2A/asterisk/{id}/afterId
     * %param id
     * %return:object
     */
    reg("/rest/test");

    /**%apidoc GET /rest/test/subscribe
     * %jsonrpc subscribe
     * %return:array
     *
     **%apidoc GET /rest/test/subscribe/{id}
     * %param id
     * %jsonrpc subscribe
     * %return:object
     *
     **%apidoc GET /rest/test/unused/{id}
     * %param id
     * %jsonrpc[unused]
     * %return:object
     */
    reg("/rest/test");

    /**%apidoc GET /rest/test/subscribeDescription
     * %jsonrpc subscribe Custom description
     * %return:array
     *
     **%apidoc GET /rest/test/subscribeDescription/{id}
     * %param id
     * %jsonrpc subscribe Custom description
     *    multiline
     * %return:object
     */
    reg("/rest/test");
