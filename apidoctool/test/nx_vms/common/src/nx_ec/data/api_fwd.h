// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#pragma once

namespace ec2 {

/**
 * Wrapper to be used for overloading as a distinct type for ApiStorageData api requests.
 */
struct ParentId
{
    QnUuid id;
    ParentId() = default;
    ParentId(const QnUuid& id): id(id) {}
};

} // namespace ec2
