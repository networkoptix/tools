// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

#include "api_data.h"

namespace ec2 {

struct ApiConnectionData : ApiData
{
    QnUuid peerId;
    QString host;
    int port = 0;

    bool operator ==(const ApiConnectionData &other) const
    {
        return peerId == other.peerId
            && host == other.host
            && port == other.port;
    }
};
#define ApiConnectionData_Fields (peerId)(host)(port)

} // namespace ec2
