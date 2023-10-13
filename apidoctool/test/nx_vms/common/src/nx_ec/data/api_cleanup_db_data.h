// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_globals.h"
#include "api_data.h"

namespace ec2
{

struct ApiCleanupDatabaseData: ApiData
{
    ApiCleanupDatabaseData():
        ApiData(),
        cleanupDbObjects(false),
        cleanupTransactionLog(false)
    {
    }

    bool cleanupDbObjects;
    bool cleanupTransactionLog;
    QString reserved;
};

#define ApiCleanupDatabaseData_Fields (cleanupDbObjects)(cleanupTransactionLog)(reserved)

}
