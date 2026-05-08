// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

    /**%apidoc GET /rest/v3/items
     * Returns a list of all items.
     * %struct ItemData
     * %return Items.
     *     %struct ItemData
     */
    reg("rest/v3/items", GlobalPermission::none);

    /**%apidoc GET /rest/v3/users
     * Returns users.
     * %struct UserData
     * %return Users.
     *     %struct UserData
     */
    reg("rest/v3/users", GlobalPermission::none);
