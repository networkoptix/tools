// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

struct NX_VMS_API DeviceAgentManifest
{
    NX_REFLECTION_ENUM_IN_CLASS(Capability,
        noCapabilities = 0,
        disableStreamSelection = 1 << 0,
        doNotSaveSettingsValuesToProperty = 1 << 31 /**< Proprietary. */
    )
    Q_DECLARE_FLAGS(Capabilities, Capability)

    Capabilities capabilities;
};
