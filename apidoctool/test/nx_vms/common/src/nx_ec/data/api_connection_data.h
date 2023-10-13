// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_data.h"
#include "api_client_info_data.h"

#include <QByteArray>
#include <QString>

namespace ec2 {

/** Parameters of connect request. */
struct ApiLoginData: ApiData
{
    QString login;
    QByteArray passwordHash;
    ApiClientInfoData clientInfo; /**< for Client use ONLY */
};

#define ApiLoginData_Fields (login)(passwordHash)(clientInfo)

} // namespace ec2
