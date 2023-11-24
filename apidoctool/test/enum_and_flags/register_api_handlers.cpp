// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

    /**%apidoc:{DeviceAgentManifest} GET /rest/v{2-}/system/metrics/manifest
     * The rules to calculate the final manifest and raise alarms. See metrics.md for details.
     * %caption Read metrics rules
     * %ingroup System
     * %return:{EngineManifest}
     */
    reg(2, "manifest", GlobalPermission::admin, std::make_unique<MetricsHandler());
