// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_data.h"

#include <nx/fusion/model_functions_fwd.h>

namespace ec2 {

struct ApiCloudSystemData: ApiData
{
    QnUuid localSystemId;
};

#define ApiCloudSystemData_Fields (localSystemId)

QN_FUSION_DECLARE_FUNCTIONS(ApiCloudSystemData, (json))

}
