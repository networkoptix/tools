// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_globals.h"
#include "api_data.h"

namespace ec2 {

struct ApiLicenseOverflowData: ApiData
{
    ApiLicenseOverflowData(): value(false), time(0) {}

    bool value;
    qint64 time;
};
#define ApiLicenseOverflowData_Fields (value)(time)

} // namespace ec2
