// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/


    /**%apidoc GET /api/storageStatus
     * Check if specified folder can be used as a server storage.
     * %param:string path Folder to check.
     * %return:object JSON data. "OK" if specified folder may be used for writing on the server.
     *     Otherwise returns "FAIL"
     */
    reg("api/storageStatus", new QnStorageStatusRestHandler());

    /**%apidoc GET /api/storageSpace
     * Return a list of all server storages.
     * %return:object JSON data with server storages.
     */
    reg("api/storageSpace", new QnStorageSpaceRestHandler());

    /**%apidoc GET /api/statistics
     * Return server info: CPU usage, HDD usage e.t.c.
     * %return:object JSON data with statistics.
     */
    reg("api/statistics", new QnStatisticsRestHandler());

    /**%apidoc GET /api/getCameraParam
     * Read camera parameters. For instance: brightness, contrast e.t.c. Parameters to read should
     * be specified.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param[opt]:string <any_name> Parameter name to read. Request can contain one or more
     *     parameters.
     * %return:object Required parameter values in form of paramName=paramValue, each parameter on
     *     a new line.
     */
    reg("api/getCameraParam", new QnCameraSettingsRestHandler());

    /**%apidoc POST /api/setCameraParam
     * Sets values of several camera parameters. This parameters are used on the Advanced tab in
     * camera settings. For instance: brightness, contrast e.t.c.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param[opt]:string <any_name> Parameter for camera to set. Request can contain one or more
     *     parameters to set.
     * %return:object "OK" if all parameters have been set, otherwise return error 500 (Internal
     *     server error) and the result of setting for every parameter.
     */
    reg("api/setCameraParam", new QnCameraSettingsRestHandler());

    /**%apidoc GET /api/manualCamera/search
     * Start searching for the cameras in manual mode.
     * %param:string start_ip First IP address in the range to scan.
     * %param[opt]:string end_ip Last IP address in the range to scan.
     * %param[opt]:integer port Camera(s) IP port to check. Port is auto-detected if this
     *     parameter is omitted.
     * %param[opt]:string user Camera(s) username.
     * %param[opt]:string password Camera(s) password.
     * %return:object JSON object with the initial status of camera search process, including
     *     processUuid used for other /api/manualCamera calls, and the list of objects describing
     *     cameras found to the moment.
     *
     **%apidoc GET /api/manualCamera/status
     * Get the current status of the process of searching for the cameras.
     * %param:uuid uuid Process unique id, can be obtained from "processUuid" field in the result
     *     of /api/manualCamera/search.
     * %return:object JSON object with the initial status of camera search process, including
     *     processUuid used for other /api/manualCamera calls, and the list of objects describing
     *     cameras found to the moment.
     *
     **%apidoc POST /api/manualCamera/stop
     * Stop manual adding progress.
     * %param:uuid uuid Process unique id, can be obtained from "processUuid" field in the result
     *     of /api/manualCamera/search.
     * %return:object JSON object with error message and error code (0 means OK).
     *
     **%apidoc[proprietary] GET /api/manualCamera/add
     * Manually add camera(s). If several cameras are added, parameters "url" and "manufacturer"
     * must be defined several times with incrementing suffix "0", "1", etc.
     * %param:string url0 Camera url, can be obtained from "reply.cameras[].url" field in the
     *     result of /api/manualCamera/status.
     * %param:string uniqueId0 Camera physical id, can be obtained from "reply.cameras[].uniqueId"
     *     field in the result of /api/manualCamera/status.
     * %param:string manufacturer0 Camera manufacturer, can be obtained from
     *     "reply.cameras[].manufacturer" field in the result of /api/manualCamera/status.
     * %param[opt]:string user Username for the cameras.
     * %param[opt]:string password Password for the cameras.
     * %return:object JSON object with error message and error code (0 means OK).
     *
     **%apidoc POST /api/manualCamera/add
     * Manually add camera(s).
     * <p>
     * Parameters should be passed as a JSON object in POST message body with
     * content type "application/json". Example of such object:
     * <pre><code>
     * {
     *     "user": "some_user",
     *     "password": "some_password",
     *     "cameras":
     *     [
     *         {
     *             "uniqueId": "00-1A-07-00-FF-FF",
     *             "url": "192.168.0.100",
     *             "manufacturer": "3100"
     *         }
     *     ]
     * }
     * </code></pre></p>
     * %param[opt]:string user Username for the cameras.
     * %param[opt]:string password Password for the cameras.
     * %param:array cameras List of objects with fields defined below.
     *     %param:string cameras[].url Camera url, can be obtained from "reply.cameras[].url"
     *         field in the result of /api/manualCamera/status.
     *     %param:string cameras[].uniqueId Camera physical id, can be obtained from
     *         "reply.cameras[].uniqueId" field in the result of /api/manualCamera/status.
     *     %param:string cameras[].manufacturer Camera manufacturer, can be obtained from
     *         "reply.cameras[].manufacturer" field in the result of /api/manualCamera/status.
     * %return:object JSON object with error message and error code (0 means OK).
     */
    reg("api/manualCamera", new QnManualCameraAdditionRestHandler());

    reg("api/wearableCamera", new QnWearableCameraRestHandler());

    /**%apidoc GET /api/ptz
     * Perform reading or writing PTZ operation
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param:enum command PTZ operation
     *     %value ContinuousMovePtzCommand Start PTZ continues move. Parameters xSpeed, ySpeed and
     *         zSpeed are used in range [-1.0..+1.0]. To stop moving use value 0 for all
     *         parameters.
     *     %value ContinuousFocusPtzCommand Start PTZ focus in or out. Parameter speed defines
     *         speed and focus direction in range [-1.0..+1.0].
     *     %value AbsoluteDeviceMovePtzCommand Move camera to absolute position. Parameters xPos,
     *         yPos and zPos are used in range defined by camera. Parameter speed is used in range
     *         [0..1.0].
     *     %value AbsoluteLogicalMovePtzCommand Move camera to absolute position. Parameters xPos,
     *         yPos range are: [-180..+180]. Parameter zPos range is: [0..180] (field of view in
     *         degree). Parameters speed range is: [0..1.0].
     *     %value GetDevicePositionPtzCommand Read camera current position. Return parameters xPos,
     *         yPos and zPos in range defined by camera.
     *     %value GetLogicalPositionPtzCommand Read camera current position. Return parameters
     *         xPos, yPos in range [-180..+180]. Return parameter zPos in range [0..180] (field of
     *         view in degree).
     *     %value CreatePresetPtzCommand Create PTZ preset. Parameter presetId defines internal
     *         preset name. Parameter presetName defines display preset name.
     *     %value UpdatePresetPtzCommand Update PTZ preset display name. Parameter presetId defines
     *         internal preset name. Parameter presetName defines display preset name.
     *     %value RemovePresetPtzCommand Update PTZ preset display name. Parameter presetId defines
     *         internal preset name
     *     %value ActivatePresetPtzCommand Go to PTZ preset. Parameter presetId defines internal
     *         preset name. Parameter speed defines move speed in range [0..1.0.]
     *     %value GetPresetsPtzCommand Read PTZ presets list.
     *     %value GetPresetsPtzCommand Read PTZ presets list.
     * %return:object JSON object with an error code (0 means OK) and error message.
     */
    reg("api/ptz", new QnPtzRestHandler());

    /**%apidoc GET /api/createEvent
     * Using this method it is possible to trigger a generic event in the system from a 3rd party
     * system. Such event will be handled and logged according to current event rules.
     * Parameters of the generated event, such as "source", "caption" and "description", are
     * intended to be analyzed by these rules.
     * <tt>
     *     <br/>Example:
     *     <pre><![CDATA[
     * http://127.0.0.1:7001/api/createEvent?timestamp=2016-09-16T16:02:41Z&caption=CreditCardUsed&metadata={"cameraRefs":["3A4AD4EA-9269-4B1F-A7AA-2CEC537D0248","3A4AD4EA-9269-4B1F-A7AA-2CEC537D0240"]}
     *     ]]></pre>
     *     This example triggers a generic event informing the system that a
     *     credit card has been used on September 16, 2016 at 16:03:41 UTC in a POS
     *     terminal being watched by the two specified cameras.
     * </tt>
     * %param[opt]:string timestamp Event date and time (as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected). If "timestamp" is absent, the current server date and
     *     time is used.
     * %param[opt]:string source Name of the device which has triggered the event. It can be used
     *     in a filter in event rules to assign different actions to different devices. Also, the
     *     user could see this name in the notifications panel. Example: "POS terminal 5".
     * %param[opt]:string caption Short event description. It can be used in a filter in event
     *     rules to assign actions depending on this text.
     * %param[opt]:string description Long event description. It can be used as a filter in event
     *     rules to assign actions depending on this text.
     * %param[opt]:objectJson metadata Additional information associated with the event, in the
     *     form of a JSON object. Currently this object can specify the only field "cameraRefs",
     *     but other fields could be added in the future. <ul> <li>"cameraRefs" specifies a number
     *     of cameras which are linked to the event (e.g. the event will appear on their
     *     timelines), in the form of a list of camera ids (can be obtained from "id" field via
     *     /ec2/getCamerasEx or /ec2/getCameras?extraFormatting). </li> </ul>
     * %param[opt]:enum state Generic events can be used either with "long" actions like
     *     "do recording", or instant actions like "send email". This parameter should be specified
     *     in case "long" actions are going to be used with generic events.
     *     %value Active Generic event is considered a "long" event. It transits to the "active"
     *         state. "Long" actions will continue executing until the generic event transits to
     *         the "inactive" state.
     *     %value Inactive A "long" action associated with this generic event in event rules will
     *         stop.
     * %return:object JSON result with error code.
     */
    reg("api/createEvent", new QnExternalEventRestHandler());

    static const char kGetTimePath[] = "api/gettime";
    /**%apidoc GET /api/gettime
     * Return server time (in milliseconds since epoch), time zone and authentication realm (realm
     * is added for convenience)
     * %return:object JSON data.
     */
    reg(kGetTimePath, new QnTimeRestHandler());

    reg("ec2/getTimeOfServers", new QnMultiserverTimeRestHandler(QLatin1String("/") + kGetTimePath));

    /**%apidoc GET /api/getTimeZones
     * Return the complete list of time zones supported by the server machine.
     * %return:object JSON object with an error code, error message, and the list of JSON objects
     *     in "reply" field:
     *     %param:string comment Time zone description in English.
     *     %param:string displayName Time zone verbose name in English.
     *     %param:boolean hasDaylightTime Whether the time zone has the DST feature.
     *         %value false
     *         %value true
     *     %param:string id Time zone identifier, to be used for e.g. /api/setTime.
     *     %param:boolean isDaylightTime Whether the time zone is on DST right now. To be reported
     *         properly, the server machine should have the correct current time set.
     *         %value false
     *         %value true
     *     %param:integer offsetFromUtc Time zone offset from UTC (in seconds).
     */
    reg("api/getTimeZones", new QnGetTimeZonesRestHandler());

    /**%apidoc GET /api/getNonce
     * Return authentication parameters: "nonce" and "realm".
     * %return:object A JSON object with an error code, error message, and the list of JSON
     *     objects in "reply" field:
     *     %param:string realm A string token used in authentication methods as "realm".
     *     %param:string nonce A session key for the current user. The current server time is used
     *         as a nonce value, and the nonce is valid for about 5 minutes.
     */
    reg("api/getNonce", new QnGetNonceRestHandler());

    reg("api/getRemoteNonce", new QnGetNonceRestHandler(lit("/api/getNonce")));
    reg("api/cookieLogin", new QnCookieLoginRestHandler());
    reg("api/cookieLogout", new QnCookieLogoutRestHandler());
    reg("api/getCurrentUser", new QnCurrentUserRestHandler());

    /**%apidoc GET /api/activateLicense
     * Activate new license and return license JSON data if success
     * %param:string key License serial number
     * %return:object JSON data.
     */
    reg("api/activateLicense", new QnActivateLicenseRestHandler());

    reg("api/testEmailSettings", new QnTestEmailSettingsHandler());

    /**%apidoc[proprietary] GET /api/getHardwareInfo
     * Get hardware information
     * %return:object JSON with hardware information.
     */
    reg("api/getHardwareInfo", new QnGetHardwareInfoHandler());

    reg("api/testLdapSettings", new QnTestLdapSettingsHandler());

    /**%apidoc GET /api/ping
     * Ping the server
     * %return:object JSON with error code, error string and module unique id in case of
     *     successful ping.
     */
    reg("api/ping", new QnPingRestHandler());

    reg(rest::helper::P2pStatistics::kUrlPath, new QnP2pStatsRestHandler());
    reg("api/recStats", new QnRecordingStatsRestHandler());

    /**%apidoc GET /api/auditLog
     * Return audit log information in the requested format.
     * %param:string from Start time of a time interval (as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     * %param[opt]:string to End time of a time interval(as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     * %return:text Tail of the server log file in text format
     */
    reg("api/auditLog", new QnAuditLogRestHandler(), kAdmin);

    reg("api/checkDiscovery", new QnCanAcceptCameraRestHandler());

    /**%apidoc GET /api/pingSystem
     * Ping the system.
     * %param:string url System URL to ping.
     * %param:string password System administrator password.
     * %return:object JSON with error code, error string and module information in case of
     *     successful ping. Error string could be empty in case of successful ping, "FAIL" if the
     *     specified system is unreachable or there is no any system, "UNAUTHORIZED" if the
     *     authentication credentials are invalid, and "INCOMPATIBLE" if the found system has
     *     incompatible version or different customization.
     */
    reg("api/pingSystem", new QnPingSystemRestHandler());

    /**%apidoc POST /api/changeCameraPassword
     * Change password for already existing user on a camera.
     * %permissions Administrator.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param:string user User name.
     * %param:string password New password to set.
     * %return:object JSON result with error code
     */
    reg("api/changeCameraPassword", new QnChangeCameraPasswordRestHandler(), kAdmin);

    /**%apidoc GET /api/rebuildArchive
     * Start or stop the server archive rebuilding, also can report this process status.
     * %param[opt]:enum action What to do and what to report about the server archive rebuild.
     *     %value start Start server archive rebuild.
     *     %value stop Stop rebuild.
     *     %value <any_other_value_or_no_parameter> Report server archive rebuild status
     * %param:integer mainPool 1 (for the main storage) or 0 (for the backup storage)
     * %return:object Rebuild progress status or an error code.
     */
    reg("api/rebuildArchive", new QnRebuildArchiveRestHandler());

    /**%apidoc GET /api/backupControl
     * Start or stop the recorded data backup process, also can report this process status.
     * %param[opt]:enum action What to do and what to report about the backup process.
     *     %value start Start backup just now.
     *     %value stop Stop backup.
     *     %value <any_other_value_or_no_parameter> Report the backup process status.
     * %return:object Bakcup process progress status or an error code.
     */
    reg("api/backupControl", new QnBackupControlRestHandler());

    /**%apidoc[proprietary] GET /api/events
     * Return event log in the proprietary binary format.
     * %param:string from Start of time period (in milliseconds since epoch).
     * %param[opt]:string to End of time period (in milliseconds since epoch).
     * %param[opt]:enum event Event type.
     * %param[opt]:enum action Action type.
     * %param[opt]:uuid brule_id Event rule id.
     * %return:binary Server event log in the proprietary binary format.
     */
    reg("api/events", new QnEventLogRestHandler(), kViewLogs); //< deprecated, still used in the client

    /**%apidoc GET /api/getEvents
     * Get server event log information.
     * %permissions At least Advanced Viewer.
     * %param:string from Start time of a time interval (as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     * %param:string to End time of a time interval (as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     * %param[opt]:string cameraId Camera id (can be obtained from "id" field via
     *     /ec2/getCamerasEx or /ec2/getCameras?extraFormatting) or MAC address (not supported for
     *     certain cameras). Used to filter events log by a single camera.
     * %param[opt]:enum event_type Filter events log by specified event type.
     * %param[opt]:enum action_type Filter events log by specified action type.
     * %param[opt]:uuid brule_id Filter events log by specified event rule (keep only records
     *     generated via that event rule). This id could be obtained via /ec2/getEventRules.
     * %return:object JSON with an error code, error message and a list of JSON objects in "reply"
     *     field:
     *     %param:enum actionType Type of the action.
     *         %value UndefinedAction
     *         %value CameraOutputAction Change camera output state.
     *         %value BookmarkAction
     *         %value CameraRecordingAction Start camera recording.
     *         %value PanicRecordingAction Activate panic recording mode.
     *         %value SendMailAction Send an email.
     *         %value DiagnosticsAction Write a record to the server's log.
     *         %value ShowPopupAction
     *         %value PlaySoundAction
     *         %value PlaySoundOnceAction
     *         %value SayTextAction
     *         %value ExecutePtzPresetAction Execute given PTZ preset.
     *         %value ShowTextOverlayAction Show text overlay over the given camera(s).
     *         %value ShowOnAlarmLayoutAction Put the given camera(s) to the Alarm Layout.
     *         %value ExecHttpRequestAction Send HTTP request as an action.
     *     %param:object actionParams JSON object with action parameters. Only fields that are
     *         applicable to the particular action are used.
     *         %param:uuid actionParams.actionResourceId Additional parameter for event log
     *             convenience.
     *         %param:string actionParams.url Play Sound / exec HTTP action.
     *         %param:string actionParams.emailAddress Email.
     *         %param:enum actionParams.userGroup Popups and System Health.
     *             %value EveryOne
     *             %value AdminOnly
     *         %param:integer actionParams.fps Frames per second for recording.
     *         %param:enum actionParams.streamQuality Stream quality for recording.
     *             %value QualityLowest
     *             %value QualityLow
     *             %value QualityNormal
     *             %value QualityHigh
     *             %value QualityHighest
     *             %value QualityPreSet
     *             %value QualityNotDefined
     *         %param:integer actionParams.recordingDuration Duration of the recording, in
     *             seconds.
     *         %param:integer actionParams.recordAfter For Bookmark, extension to the recording
     *             time, in seconds.
     *         %param:string actionParams.relayOutputId Camera Output.
     *         %param:string actionParams.sayText
     *         %param:string actionParams.tags Bookmark.
     *         %param:string actionParams.text Text for Show Text Overlay, or message body for
     *             Exec HTTP Action.
     *         %param:integer actionParams.durationMs Duration in milliseconds for Bookmark and
     *             Show Text Overlay.
     *         %param:arrayJson actionParams.additionalResources JSON list of ids of additional
     *             resources; user ids for Show On Alarm Layout.
     *         %param:boolean actionParams.forced Alarm Layout - if it must be opened immediately.
     *             %value true
     *             %value false
     *         %param:string actionParams.presetId Execute PTZ preset action.
     *         %param:boolean actionParams.useSource Alarm Layout - if the source resource should
     *             also be used.
     *         %param:integer actionParams.recordBeforeMs Bookmark start time is adjusted to the
     *             left by this value in milliseconds.
     *         %param:boolean actionParams.playToClient Text to be pronounced.
     *         %param:string actionParams.contentType HTTP action.
     *     %param:object eventParams JSON object with event parameters.
     *         %param:enum eventParams.eventType Type of the event.
     *             %value UndefinedEvent Event type is not defined. Used in rules.
     *             %value CameraMotionEvent Motion has occurred on a camera.
     *             %value CameraInputEvent Camera input signal is received.
     *             %value CameraDisconnectEvent Camera was disconnected.
     *             %value StorageFailureEvent Storage read error has occurred.
     *             %value NetworkIssueEvent Network issue: packet lost, RTP timeout, etc.
     *             %value CameraIpConflictEvent Found some cameras with same IP address.
     *             %value ServerFailureEvent Connection to server lost.
     *             %value ServerConflictEvent Two or more servers are running.
     *             %value ServerStartEvent Server started.
     *             %value LicenseIssueEvent Not enough licenses.
     *             %value BackupFinishedEvent Archive backup done.
     *             %value SystemHealthEvent System health message.
     *             %value MaxSystemHealthEvent System health message.
     *             %value AnyCameraEvent Event group.
     *             %value AnyServerEvent Event group.
     *             %value AnyBusinessEvent Event group.
     *             %value UserDefinedEvent Base index for the user-defined events.
     *         %param:integer eventParams.eventTimestampUsec When did the event occur, in
     *             microseconds.
     *         %param:uuid eventParams.eventResourceId Event source - camera or server id.
     *         %param:string eventParams.resourceName Name of the resource which caused the event.
     *             Used if no resource is actually registered in the system. Generic event can
     *             provide some resource name which doesn't match any resourceId in the system. In
     *             this case resourceName is filled and resourceId remains empty.
     *         %param:uuid eventParams.sourceServerId Id of a server that generated the event.
     *         %param:enum eventParams.reasonCode Used in Reasoned Events as a reason code.
     *             %value NoReason
     *             %value NetworkNoFrameReason
     *             %value NetworkConnectionClosedReason
     *             %value NetworkRtpPacketLossReason
     *             %value ServerTerminatedReason
     *             %value ServerStartedReason
     *             %value StorageIoErrorReason
     *             %value StorageTooSlowReason
     *             %value StorageFullReason
     *             %value LicenseRemoved
     *             %value BackupFailedNoBackupStorageError
     *             %value BackupFailedSourceStorageError
     *             %value BackupFailedSourceFileError
     *             %value BackupFailedTargetFileError
     *             %value BackupFailedChunkError
     *             %value BackupEndOfPeriod
     *             %value BackupDone
     *             %value BackupCancelled
     *             %value NetworkNoResponseFromDevice
     *         %param:string eventParams.inputPortId Used for Input events only.
     *         %param:string eventParams.caption Short event description. Used for camera/server
     *             conflict as resource name which cause error. Used in generic events as a short
     *             description.
     *         %param:string eventParams.description Long event description. Used for
     *             camera/server conflict as a long description (conflict list). Used in Reasoned
     *             Events as reason description. Used in generic events as a long description.
     *         %param:arrayJson eventParams.metadata Camera list which is associated with the
     *             event. EventResourceId may be a POS terminal, but this is a camera list which
     *             should be shown with this event.
     *     %param:uuid businessRuleId Id of the event rule.
     *     %param:integer aggregationCount Number of identical events groupped into one.
     *     %param[proprietary]:flags flags Combination (via "|") or the following flags:
     *         %value VideoLinkExists
     */
    reg("api/getEvents", new QnEventLog2RestHandler(), kViewLogs); //< new version

    /**%apidoc GET /api/showLog
     * Return tail of the server log file
     * %param[opt]:integer lines Display last N log lines.
     * %param[opt]:integer id Id of log file. By default main log is returned
     *     %value 0 Main server log
     *     %value 2 Http log
     *     %value 3 Transaction log
     * %return:text Tail of the server log file in text format
     */
    reg("api/showLog", new QnLogRestHandler());

    reg("api/getSystemId", new QnGetSystemIdRestHandler());

    /**%apidoc GET /api/doCameraDiagnosticsStep
     * Performs camera diagnostics.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param:enum type Diagnostics to perform.
     *     %value mediaServerAvailability Checks server availability
     *     %value cameraAvailability Checks if camera is accessible from the server
     *     %value mediaStreamAvailability Checks if camera media stream can be opened
     *     %value mediaStreamIntegrity Checks additional media stream parameters
     * %return:object JSON object with an error code, error message and diagnostics result.
     */
    reg("api/doCameraDiagnosticsStep", new QnCameraDiagnosticsRestHandler());

    /**%apidoc[proprietary] POST /api/installUpdate
     * Updates server by the package contained in POST body
     * %return:object JSON with error code.
     *     When all is OK errorString will be empty. In case of error errorString will contain:
     *     UP_TO_DATE if the provided version is already installed;
     *     INVALID_FILE if the provided file cannot be opened as a ZIP archive;
     *     INCOMPATIBLE_SYSTEM if the update file is targeted for another system;
     *     EXTRACTION_ERROR if some extraction problems were found (e.g. not enough space);
     *     INSTALLATION_ERROR if the server could not execute installation script.
     */
    reg("api/installUpdate", new QnUpdateRestHandler());

    reg("api/installUpdateUnauthenticated", new QnUpdateUnauthenticatedRestHandler());

    /**%apidoc GET /api/restart
     * Restarts the server.
     * %permissions Administrator.
     * %return:object JSON with error code.
     */
    reg("api/restart", new QnRestartRestHandler(), kAdmin);

    reg("api/connect", new QnOldClientConnectRestHandler());

    /**%apidoc GET /api/moduleInformation
     * Get information about the server.
     * %param[opt]:boolean allModules Set it to true to get all modules from the system.
     * %param[opt]:boolean showAddresses Set it to true to show server addresses.
     * %return:object JSON object with module information.
     */
    reg("api/moduleInformation", new QnModuleInformationRestHandler());

    /**%apidoc GET /api/iflist
     * Get network settings (list of interfaces) for the server. Can be called only if server flags
     * include "SF_IfListCtrl" (server flags can be obtained via /ec2/getMediaServersEx in
     * "flags" field).
     * %return:object List of objects with interface parameters.
     *     %param:string  name Interface name.
     *     %param:string ipAddr IP address with dot-separated decimal components.
     *     %param:string netMask Network mask with dot-separated decimal components.
     *     %param:string mac MAC address with colon-separated upper-case hex components.
     *     %param:string gateway IP address of the gateway with dot-separated decimal components.
     *         Can be empty.
     *     %param:boolean dhcp
     *         %value false DHCP is not used, IP address and other parameters should be specified
     *             in the respective JSON fields.
     *         %value true IP address and other parameters assigned via DHCP, the respective JSON
     *             fields can be empty.
     *     %param:object extraParams JSON object with data in the internal format.
     *     %param:string dns_servers Space-separated list of IP addresses with dot-separated
     *         decimal components.
     */
    reg("api/iflist", new QnIfListRestHandler());

    /**%apidoc GET /api/aggregator
     * This function allows to execute several requests with json content type and returns result
     * as a single JSON object
     * %param[opt]:string exec_cmd HTTP url path to execute. This parameter could be repeated
     *     several times to execute several nested methods. All additions parameters after current
     *     "exec_cmd" and before next "exec_cmd" are passed as parameters to the nested method.
     * %return:object Merged JSON data from nested methods.
     */
    reg("api/aggregator", new QnJsonAggregatorRestHandler());

    /**%apidoc POST /api/ifconfig
     * Set new network settings (list of interfaces) for the server. Can be called only if server
     * flags include "SF_IfListCtrl" (server flags can be obtained via /ec2/getMediaServersEx
     * in "flags" field). <p> Parameters should be passed as a JSON array of objects in POST
     * message body with content type "application/json". Example of such object can be seen in
     * the result of GET /api/iflist function. </p>
     * %permissions Administrator.
     * %param:string name Interface name.
     * %param:string ipAddr IP address with dot-separated decimal components.
     * %param:string netMask Network mask with dot-separated decimal components.
     * %param:string  mac MAC address with colon-separated upper-case hex components.
     * %param:string gateway IP address of the gateway with dot-separated decimal components. Can
     *     be empty.
     * %param:boolean dhcp
     *     %value false DHCP is not used, IP address and other parameters should be specified in
     *         the respective JSON fields.
     *     %value true IP address and other parameters assigned via DHCP, the respective JSON
     *         fields can be empty.
     * %param:object extraParams JSON object with data in the internal format.
     * %param:string dns_servers Space-separated list of IP addresses with dot-separated decimal
     *     components.
     */
    reg("api/ifconfig", new QnIfConfigRestHandler(), kAdmin);

    reg("api/downloads/", new QnDownloadsRestHandler());


    /**%apidoc[proprietary] GET /api/settime
     * Set current time on the server machine. Can be called only if server flags include
     * "SF_timeCtrl" (server flags can be obtained via /ec2/getMediaServersEx in "flags"
     * field).
     * %permissions Administrator.
     * %param[opt]:string timezone Time zone identifier, can be obtained via /api/getTimeZones.
     * %param:string datetime System date and time (as a string containing time in milliseconds
     *     since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     */
    reg("api/settime", new QnSetTimeRestHandler(), kAdmin); //< deprecated

    /**%apidoc POST /api/setTime
     * Set current time on the server machine.
     * Can be called only if server flags include "SF_timeCtrl"
     * (server flags can be obtained via /ec2/getMediaServersEx in "flags" field).
     * <p>
     *     Parameters should be passed as a JSON object in POST message body with
     *     content type "application/json". Example of such object:
     * <pre><code>
     * {
     *     "dateTime": "2015-02-28T16:37:00",
     *     "timeZoneId": "Europe/Moscow"
     * }
     * </code>
     * </pre>
     * </p>
     * %permissions Administrator.
     * %param[opt]:string timeZoneId Time zone identifier, can be obtained via /api/getTimeZones.
     * %param:string dateTime Date and time (as string containing time in milliseconds since
     *     epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     */
    reg("api/setTime", new QnSetTimeRestHandler(), kAdmin); //< new version

    /**%apidoc GET /api/moduleInformationAuthenticated
     * The same as moduleInformation but requires authentication. Useful to test connection.
     * %return:object JSON object with module information.
     */
    reg("api/moduleInformationAuthenticated", new QnModuleInformationRestHandler());

    /**%apidoc POST /api/configure
     * Configure various server parameters.
     * %permissions Administrator.
     * %param[opt]:string systemName System display name. It affects all servers in the system.
     * %param[opt]:integer port Server API port. It affects the current server only.
     * %return JSON with error code, error string, and flag "restartNeeded" that shows whether the
     *     server must be restarted to apply settings. Error string contains a hint to identify the
     *     problem: "SYSTEM_NAME" or "PORT".
     */
    reg("api/configure", new QnConfigureRestHandler(messageBus), kAdmin);

    /**%apidoc POST /api/detachFromCloud
     * Detach media server from cloud. Local admin user is enabled, admin password is changed to
     * new value (if specified), all cloud users are disabled. Cloud link is removed. Function can
     * be called either via GET or POST method. POST data should be a json object.
     * %permissions Administrator.
     * %param[opt]:string password Set new admin password after detach.
     * %return JSON result with error code
     */
    reg("api/detachFromCloud", new QnDetachFromCloudRestHandler(
        &cloudManagerGroup->connectionManager), kAdmin);

    reg("api/detachFromSystem", new QnDetachFromSystemRestHandler(
        &cloudManagerGroup->connectionManager, messageBus), kAdmin);

    /**%apidoc[proprietary] POST /api/restoreState
     * Restore server state to default. Cleans database and system name.
     * %permissions Administrator.
     * %param:string oldPassword Current admin password
     * %return:object JSON result with an error code and an error string.
     */
    reg("api/restoreState", new QnRestoreStateRestHandler(), kAdmin);

    /**%apidoc POST /api/setupLocalSystem
     * Configure server system name and password. This function can be called for server with
     * default system name. Otherwise function returns error. This method requires owner
     * permissions.
     * %permissions Administrator.
     * %param:string password New password for admin user
     * %param:string systemName New system name
     * %return:object JSON result with error code
     */
    reg("api/setupLocalSystem", new QnSetupLocalSystemRestHandler(), kAdmin);

    /**%apidoc POST /api/setupCloudSystem
     * Configure server system name and attach it to cloud. This function can be called for server
     * with default system name. Otherwise function returns error. This method requires owner
     * permissions.
     * %permissions Administrator.
     * %param:string systemName New system name
     * %param:string cloudAuthKey could authentication key
     * %param:string cloudSystemID could system id
     * %return:object JSON result with error code
     */
    reg("api/setupCloudSystem", new QnSetupCloudSystemRestHandler(cloudManagerGroup), kAdmin);

    /**%apidoc POST /api/mergeSystems
     * Merge two Systems. <br/> The System that joins another System is called the current System,
     * the joinable System is called the target System. The <b>URL</b> parameter sets the
     * target Server which should be joined with the current System. Other servers, that are
     * merged with the target Server will be joined if parameter <b>mergeOneServer</b> is set
     * to false. <br/> The method uses digest authentication. Two hashes should be previouly
     * calculated: <b>getKey</b> and <b>postKey</b>. Both are mandatory. The calculation
     * algorithm is described in <b>Calculating authentication hash</b> section (in the bootom
     * of the page). While calculating hashes, username and password of the target Server are
     * needed. Digest authentication needs realm and nonce, both can be obtained with <code>GET
     * /api/getNonce call</code> call. The lifetime of a nonce is about a few minutes.
     * %permissions Administrator.
     * %param:string url URL of one Server in the System to join.
     * %param:string getKey Authentication hash of the target Server for GET requests.
     * %param:string postKey Authentication hash of the target Server for POST requests.
     * %param[opt]:boolean takeRemoteSettings Direction of the merge. Default value is false. If
     *     <b>mergeOneServer</b> is true, <b>takeRemoteSettings</b> parameter is ignored and
     *     treated as false.
     *     %value true The current system will get system name and administrator password of the
     *         target system.
     *     %value false The target system will get system name and administrator password of the
     *         current system.
     * %param[opt]:boolean mergeOneServer Whether to merge with servers merged with the target
     *     server. Default value is false. If <b>mergeOneServer</b> is set to true,
     *     <b>takeRemoteSettings</b> is ignored and treated as false.
     *     %value true The current system will merge with target server only. The target server
     *         will be disjoined from another system (if it was joined).
     *     %value false The current system will merge with target server and all servers which are
     *         merged with the target server.
     * %param[opt]:boolean ignoreIncompatible Whether to ignore different version of merged server
     *     protocols. Default value is false.
     *     %value true Merge will start anyway.
     *     %value false If the target server protocol version differs from the current server
     *         protocol version merge aborts.
     * %return:object JSON with error code and error string. Error string could be empty in case
     *     of successful ping, "FAIL" if the specified system is unreachable or there is no system,
     *     "UNAUTHORIZED" if the authentication credentials are invalid, "INCOMPATIBLE" if the
     *     found system has incompatible version or different customization, and "BACKUP_ERROR" if
     *     database backup could not been created.
     */
    reg("api/mergeSystems", new QnMergeSystemsRestHandler(messageBus), kAdmin);

    /**%apidoc GET /api/backupDatabase
     * Back up server database.
     * %return:object JSON with error code.
     */
    reg("api/backupDatabase", new QnBackupDbRestHandler());

    /**%apidoc GET /api/discoveredPeers
     * Return a list of the discovered peers.
     * %return:object JSON with a list of the discovered peers.
     */
    reg("api/discoveredPeers", new QnDiscoveredPeersRestHandler());

    /**%apidoc GET /api/logLevel
     * Get or set server log level.
     * %param[opt]:integer id Log id
     *     %value 0 Main server log
     *     %value 2 Http log
     *     %value 3 Transaction log
     * %param[opt]:enum value Target value for log level. More detailed level includes all less
     *     detailed levels.
     *     %value None Disable log.
     *     %value Always Log only the most important messages.
     *     %value Error Log errors.
     *     %value Warning Log warnings.
     *     %value Info Log information messages.
     *     %value Debug Log debug messages.
     *     %value Debug2 Log additional debug messages.
     */
    reg("api/logLevel", new QnLogLevelRestHandler());

    /**%apidoc[proprietary] GET /api/execute
     * Execute any script from subfolder "scripts" of media server. Script name provides directly
     * in a URL path like "/api/execute/script1.sh". All URL parameters are passed directly to
     * a script as an parameters.
     * %permissions Administrator.
     * %return:object JSON with error code.
     */
    reg("api/execute", new QnExecScript(), kAdmin);

    /**%apidoc[proprietary] GET /api/scriptList
     * Return list of scripts to execute.
     * %permissions Administrator.
     * %return:object JSON object with string list.
     */
    reg("api/scriptList", new QnScriptListRestHandler(), kAdmin);

    /**%apidoc GET /api/systemSettings
     * Get or set global system settings. If called with no arguments, just returns list of all
     * system settings with their values
     * %param[opt]:string <param_name> name of system parameter. E.g., ec2AliveUpdateIntervalSec
     * %param[opt]:string <param_value> New value for the specified parameter
     */
    reg("api/systemSettings", new QnSystemSettingsHandler());

    reg("api/transmitAudio", new QnAudioTransmissionRestHandler());

    // TODO: Introduce constants for API methods registered here, also use them in
    // media_server_connection.cpp. Get rid of static/global urlPath passed to some handler ctors,
    // except when it is the path of some other api method.

    reg("api/RecordedTimePeriods", new QnRecordedChunksRestHandler()); //< deprecated

    /**%apidoc GET /ec2/recordedTimePeriods
     * Return the recorded chunks info for the specified cameras.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     *     This parameter can be used several times to define a list of cameras.
     * %param[opt]:string startTime Start time of the interval (as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     * %param[opt]:string endTime End time of the interval (as a string containing time in
     *     milliseconds since epoch, or a local time formatted like
     *     <code>"<i>YYYY</i>-<i>MM</i>-<i>DD</i>T<i>HH</i>:<i>mm</i>:<i>ss</i>.<i>zzz</i>"</code>
     *     - the format is auto-detected).
     * %param[opt]:arrayJson filter This parameter is used for motion search ("periodsType" must
     *     be 1). Match motion on a video by specified rectangle.
     *     <br/>Format: string with a JSON list of <i>sensors</i>,
     *     each <i>sensor</i> is a JSON list of <i>rects</i>, each <i>rect</i> is:
     *     <br/>
     *     <code>
     *         {"x": <i>x</i>, "y": <i>y</i>, "width": <i>width</i>,"height": <i>height</i>}
     *     </code>
     *     <br/>All values are measured in relative portions of a video frame,
     *     <i>x</i> and <i>width</i> in range [0..43], <i>y</i> and <i>height</i> in range [0..31],
     *     zero is the left-top corner.
     *     <br/>Example of a full-frame rectangle for a single-sensor camera:
     *     <code>[[{"x":0,"y":0,"width":43,"height":31}]]</code>
     *     <br/>Example of two rectangles for a single-sensor camera:
     *     <code>[[{"x":0,"y":0,"width":5,"height":7},{"x":12,"y":10,"width":8,"height":6}]]</code>
     * %param[proprietary]:enum format Data format. Default value is "json".
     *     %value ubjson Universal Binary JSON data format.
     *     %value json JSON data format.
     *     %value periods Internal comperssed binary format.
     * %param[opt]:integer detail Chunk detail level, in microseconds. Time periods that are
     *     shorter than the detail level are discarded. You can treat the detail level as the
     *     amount of microseconds per screen pixel.
     * %param[opt]:integer periodsType Chunk type.
     *     %value 0 All records.
     *     %value 1 Only chunks with motion (parameter "filter" is required).
     * %param[opt]:option keepSmallChunks If specified, standalone chunks smaller than the detail
     *     level are not removed from the result.
     * %param[opt]:integer limit Maximum number of chunks to return.
     * %param[opt]:option flat If specified, do not group chunk lists by server.
     * %return:object JSON object with an error code, error message and the list of JSON objects
     *     in "reply" field: if no "flat" parameter is specified, "reply" field is the list which
     *     contains for each server its GUID (as "guid" field) and the list of chunks (as "periods"
     *     field); if "flat" parameter is specified, "reply" field is just the list of chunks.
     *     <br/>Each chunk is a pair of <code>(durationMs, startTimeMs)</code>. Chunks are merged
     *     for all requested cameras. Start time and duration are in milliseconds since epoch.
     *     Duration of -1 means the last chunk is being recorded now.
     */
    reg("ec2/recordedTimePeriods", new QnMultiserverChunksRestHandler("ec2/recordedTimePeriods")); //< new version

    reg("ec2/cameraHistory", new QnCameraHistoryRestHandler());

    /**%apidoc GET /ec2/bookmarks
     * Read bookmarks using the specified parameters.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param[opt]:string startTime Start time of the interval with bookmarks (in milliseconds
     *     since epoch). Default value is 0. Should be less than endTime.
     * %param[opt]:string endTime End time of the interval with bookmarks (in milliseconds since
     *     epoch). Default value is the current time. Should be greater than startTime.
     * %param[opt]:enum sortBy Field to sort the results by. Default value is "startTime".
     *     %value name Sort bookmarks by name.
     *     %value startTime Sort bookmarks by start time.
     *     %value duration Sort bookmarks by duration.
     *     %value cameraName Sort bookmarks by camera name.
     * %param[opt]:enum sortOrder Sort order. Default order is ascending.
     *     %value asc Ascending sort order.
     *     %value desc Descending sort order.
     * %param[opt]:integer limit Maximum number of bookmarks to return. Unlimited by default.
     * %param[opt]:string filter Text-search filter string.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     *
     **%apidoc GET /ec2/bookmarks/add
     * Add a bookmark to the target server.
     * %param:uuid guid Identifier of the bookmark.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param:string name Caption of the bookmark.
     * %param[opt]:string description Details of the bookmark.
     * %param[opt]:integer timeout Time during which the recorded period should be preserved (in
     *     milliseconds).
     * %param:integer startTime Start time of the bookmark (in milliseconds since epoch).
     * %param:integer duration Length of the bookmark (in milliseconds).
     * %param[opt]:string tag Applied tag. Several tag parameters could be used to specify multiple tags.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     *
     **%apidoc GET /ec2/bookmarks/delete
     * Remove a bookmark with the specified identifier.
     * %param:uuid guid Identifier of the bookmark.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     *
     **%apidoc GET /ec2/bookmarks/tags
     * Return currently used tags.
     * %param[opt]:integer limit Maximum number of tags to return.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     *
     **%apidoc GET /ec2/bookmarks/update
     * Update information for a bookmark.
     * %param:uuid guid Identifier of the bookmark.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param:string name Caption of the bookmark.
     * %param[opt]:string  description Details of the bookmark.
     * %param[opt]:integer timeout Time during which the recorded period should be preserved (in
     *     milliseconds).
     * %param:integer startTime Start time of the bookmark (in milliseconds since epoch).
     * %param:integer duration Length of the bookmark (in milliseconds).
     * %param[opt]:string tag Applied tag. Serveral tag parameters could be used to specify
     *     multiple tags.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     */
    reg("ec2/bookmarks", new QnMultiserverBookmarksRestHandler("ec2/bookmarks"));

    reg("api/mergeLdapUsers", new QnMergeLdapUsersRestHandler());

    /**%apidoc[proprietary] GET /ec2/updateInformation/freeSpaceForUpdateFiles
     * Get free space available for downloading and extracting update files.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     * %return The amount of free space available for update files in bytes for each online server
     *     in the system, in the specified format.
     */
    reg("ec2/updateInformation", new QnUpdateInformationRestHandler());

    /**%apidoc GET /ec2/cameraThumbnail
     * Get the static image from the camera.
     * %param:string cameraId Camera id (can be obtained from "id" field via /ec2/getCamerasEx or
     *     /ec2/getCameras?extraFormatting) or MAC address (not supported for certain cameras).
     * %param[opt]:string time Timestamp of the requested image (in milliseconds since epoch).
     *     The special value "latest", which is the default value, requires to retrieve the latest
     *     thumbnail. The special value "now" requires to retrieve the thumbnail corresponding to
     *     the current time.
     * %param[opt]:integer rotate Image orientation. Can be 0, 90, 180 or 270 degrees. If the
     *     parameter is absent or equals -1, the image will be rotated as defined in the camera
     *     settings.
     * %param[opt]:integer height Desired image height. Should be not less than 128, or equal to
     *     -1 (the default value) which implies the original frame size, and in this case the width
     *     should also be omitted or set to -1.
     * %param[opt]:integer width Desired image width. Should be not less than 128, or equal to -1
     *     (the default value) which implies autosizing: if the height is specified, the width will
     *     be calculated based on the aspect ratio, otherwise, the original frame size will be
     *     used.
     * %param[opt]:enum imageFormat Format of the requested image. Default value is "JpgFormat".
     *     %value png PNG
     *     %value jpg JPEG
     *     %value tif TIFF
     *     %value raw Raw video frame. Makes the request much more lightweight for Edge servers.
     * %param[opt]:enum roundMethod Getting a thumbnail at the exact timestamp is costly, so, it
     *     can be rounded to the nearest keyframe, thus, the default value is
     *     "KeyFrameAfterMethod".
     *     %value before Get the thumbnail from the nearest keyframe before the given time.
     *     %value precise Get the thumbnail as near to given time as possible.
     *     %value after Get the thumbnail from the nearest keyframe after the given time.
     * %param[opt]:enum aspectRatio Allows to avoid scaling the image to the aspect ratio from
     *     camera settings.
     *     %value auto Default value. Use aspect ratio from camera settings (if any).
     *     %value source Use the source frame aspect ratio, despite the value in camera settings.
     * %param[proprietary]:option local If present, the request should not be redirected to another
     *     server.
     * %param[proprietary]:option extraFormatting If present and the requested result format is
     *     non-binary, indentation and spacing will be used to improve readability.
     * %param[default]:enum format
     */
    reg("ec2/cameraThumbnail", new QnMultiserverThumbnailRestHandler("ec2/cameraThumbnail"));

    reg("ec2/statistics", new QnMultiserverStatisticsRestHandler("ec2/statistics"));

    /**%apidoc POST /api/saveCloudSystemCredentials
     * Sets or resets cloud credentials (systemId and authorization key) to be used by system
     * %param[opt]:string cloudSystemId
     * %param[opt]:string cloudAuthenticationKey
     * %param[opt]:string reset
     *     %value true If specified, removes cloud credentials from DB. System will not connect to
     *         cloud anymore
     */
    reg("api/saveCloudSystemCredentials", new QnSaveCloudSystemCredentialsHandler(cloudManagerGroup));

    reg("favicon.ico", new QnFavIconRestHandler());
    reg("api/dev-mode-key", new QnCrashServerHandler(), kAdmin);

    reg("api/startLiteClient", new QnStartLiteClientRestHandler());

    #if defined(_DEBUG)
        reg("api/debugEvent", new QnDebugEventsRestHandler());
    #endif

    reg("ec2/runtimeInfo", new QnRuntimeInfoRestHandler());

    static const char kGetHardwareIdsPath[] = "api/getHardwareIds";
    /**%apidoc GET /api/getHardwareIds
     * Return the list of Hardware Ids of the server.
     * %return:object JSON with an error code, error message and a list of strings in "reply"
     *     field.
     */
    reg(kGetHardwareIdsPath, new QnGetHardwareIdsRestHandler());

    /**%apidoc GET /ec2/getHardwareIdsOfServers
     * Return the list of Hardware Ids for each server in the system which is online at the moment
     * of executing this function.
     * %return:object JSON with an error code, error message and a list of JSON objects in "reply"
     *     field:
     *     %param:uuid serverId Id of a server.
     *     %param:stringArray hardwareIds All Hardware Ids of the server, as a list of strings.
     */
    reg("ec2/getHardwareIdsOfServers", new QnMultiserverGetHardwareIdsRestHandler(QLatin1String("/") + kGetHardwareIdsPath));
