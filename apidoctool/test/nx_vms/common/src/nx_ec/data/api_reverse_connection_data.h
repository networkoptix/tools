// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_data.h"

#include <QByteArray>
#include <QString>

namespace ec2 {

/** Request to open count proxy connections to @var target server. */
struct ApiReverseConnectionData: ApiData
{
    QnUuid targetServer;
    int socketCount = 0;
};
#define ApiReverseConnectionData_Fields (targetServer)(socketCount)

} // namespace ec2

Q_DECLARE_METATYPE(ec2::ApiReverseConnectionData);
