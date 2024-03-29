// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_globals.h"
#include "api_data.h"

namespace ec2 {

struct ApiPropertyTypeData: ApiData
{
    QnUuid resourceTypeId;
    QString name;
    QString defaultValue;
};
#define ApiPropertyTypeData_Fields (resourceTypeId)(name)(defaultValue)

struct ApiResourceTypeData: ApiIdData
{
    QString name;
    QString vendor;
    std::vector<QnUuid> parentId;
    std::vector<ApiPropertyTypeData> propertyTypes;
};
#define ApiResourceTypeData_Fields ApiIdData_Fields (name)(vendor)(parentId)(propertyTypes)

}
