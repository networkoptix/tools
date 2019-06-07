#!/bin/bash

nxCmake()
{
    nx_verbose cmake "$@"
}

# [in] CMAKE_GEN_OPTIONS (optional)
# [in] CMAKE_BUILD_OPTIONS (optional)
# [in] TOOLCHAIN_PREFIX (optional)
# [in] DESTDIR or SYSROOT
cmakeBuild()
{
    if [[ -n ${TOOLCHAIN_PREFIX:-} ]]
    then
        setToolchain "${TOOLCHAIN_PREFIX}"
    fi

    nxCmake -G "Unix Makefiles" "${CMAKE_GEN_OPTIONS[@]}" .

    nxCmake --build "${CMAKE_BUILD_OPTIONS[@]}" .

    nxMake install DESTDIR="${DESTDIR:-${SYSROOT}}"
}

