// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_globals.h"
#include "api_data.h"

namespace ec2 {

struct ApiLockData: ApiData
{
    QString name;
    QnUuid peer;
    qint64 timestamp = 0;
    QByteArray userData;
};
#define ApiLockData_Fields (name)(peer)(timestamp)(userData)

} // namespace ec2

Q_DECLARE_METATYPE(ec2::ApiLockData)
