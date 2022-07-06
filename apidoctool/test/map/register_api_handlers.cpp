    /**%apidoc GET /rest/v{2-}/system/metrics/rules
     * The rules to calculate the final manifest and raise alarms. See metrics.md for details.
     * %caption Read metrics rules
     * %ingroup System
     * %permissions Admin.
     * %param[ref] _local
     * %param[ref] _keepDefault
     * %param[ref] _with
     * %return:{std::map<QString, ResourceRules>} Structure of rules.
     */
    reg(2, "metrics/rules", GlobalPermission::admin,
        std::make_unique<MetricsHandler<api::metrics::SystemRules>>(systemController, serverModule->commonModule(), serverConnector));
