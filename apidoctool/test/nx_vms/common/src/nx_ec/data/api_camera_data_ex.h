// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_globals.h"
#include "api_camera_data.h"
#include "api_camera_attributes_data.h"

namespace ec2 {

struct ApiCameraDataEx:
    ApiCameraData,
    ApiCameraAttributesData
{
    Qn::ResourceStatus status;
    std::vector<ApiResourceParamData> addParams;
};
#define ApiCameraDataEx_Fields \
    ApiCameraData_Fields ApiCameraAttributesData_Fields_Short (status)(addParams)

} // namespace ec2
