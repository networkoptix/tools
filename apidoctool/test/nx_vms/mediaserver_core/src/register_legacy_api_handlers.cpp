// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

#include "register_legacy_api_handlers.h"

#include <nx/vms/server/rest/analytics_engine_settings_handler.h>

void registerLegacyApiHandlers(
    MediaServerProcess* process,
    nx::vms::network::AbstractServerConnector* serverConnector,
    nx::vms::utils::metrics::SystemController* metricsController)
{

    /**%apidoc GET /ec2/analyticsEngineSettings
     * Return values of settings of the specified Engine.
     * %param:string analyticsEngineId Id of an Analytics Engine.
     * %return
     *     %struct Result
     *     %param[opt]:object reply Object with Engine settings model and values.
     *         %struct EngineSettingsResponse
     *
     **%apidoc POST /ec2/analyticsEngineSettings
     * Applies passed settings values to correspondent Analytics Engine.
     * %struct EngineSettingsRequest
     * %return
     *     %struct Result
     *     %param[opt]:object reply Object with Engine settings model and values that the Engine
     *         returns after the values have been supplied.
     *         %struct EngineSettingsResponse
     */
    reg("ec2/analyticsEngineSettings",
        new nx::vms::server::rest::AnalyticsEngineSettingsHandler(serverModule));
