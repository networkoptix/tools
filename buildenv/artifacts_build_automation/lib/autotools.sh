#!/bin/bash

nxConfigure()
{
    nx_verbose ./configure "$@"
}

# [in] AUTOCONF_OPTIONS (optional)
# [in] TOOLCHAIN_PREFIX (optional)
# [in] DESTDIR or SYSROOT
autotoolsBuild()
{
    setToolchainMediatorVars

    export PKG_CONFIG_PATH="$SYSROOT/usr/lib/pkgconfig"

    nxConfigure "${AUTOCONF_OPTIONS[@]}"

    nxMake

    nxMake install DESTDIR="${DESTDIR:-${SYSROOT}}"
}

