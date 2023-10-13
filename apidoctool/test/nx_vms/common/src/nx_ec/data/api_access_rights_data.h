// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include <nx_ec/data/api_data.h>

namespace ec2 {

struct ApiAccessRightsData: ApiData
{
    QnUuid userId;
    std::vector<QnUuid> resourceIds;
};
#define ApiAccessRightsData_Fields (userId)(resourceIds)

} // namespace ec2
