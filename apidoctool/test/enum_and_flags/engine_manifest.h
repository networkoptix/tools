// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

struct NX_VMS_API EngineManifest
{
    NX_REFLECTION_ENUM_CLASS_IN_CLASS(Capability,
        noCapabilities = 0,
        needUncompressedVideoFrames_yuv420 = 1 << 0,
        needUncompressedVideoFrames_argb = 1 << 1,
        needUncompressedVideoFrames_abgr = 1 << 2,
        needUncompressedVideoFrames_rgba = 1 << 3,
        needUncompressedVideoFrames_bgra = 1 << 4,
        needUncompressedVideoFrames_rgb = 1 << 5,
        needUncompressedVideoFrames_bgr = 1 << 6,
        deviceDependent = 1 << 7,
        keepObjectBoundingBoxRotation = 1 << 8,
        noAutoBestShots = 1 << 9
    )
    Q_DECLARE_FLAGS(Capabilities, Capability)

    Capabilities capabilities;
};
