# Network Optix VMS Desktop Client build package

This directory contains the package of source code and pre-built third-party artifacts needed to
build the Network Optix VMS Desktop Client.

---------------------------------------------------------------------------------------------------
## Legal notice

The whole contents of this package is considered proprietary to Network Optix, except for the
particular files licensed by third-party under one of the open-source licenses.

The product built from this package is intended for technical experiments only, and must not be
used for end-user purposes as part of a VMS.

---------------------------------------------------------------------------------------------------
## General information

Commit: 178db5269af5
Customization: MetaVMS
Version: 4.3.0
Meta-version: R2-OPEN

The built Client can connect to the corresponding MetaVMS Server 4.3.0 R2.

Supported platforms: Windows x64, Linux x64.

Building distribution packages (MSI for Windows, .deb for Linux) is not supported by this package.

### Contents

conan/
    Third-party pre-built and header-only packages, originally managed by conan, but included here
    to avoid using conan.

packages/
    Other third-party pre-built and header-only packages.
    
nx/
    Source code.
   
---------------------------------------------------------------------------------------------------
## Build environment

### Python

Python 3.8+ should be installed and available on PATH as `python`.

Windows: a Windows-native (non-Cygwin) version of Python should be installed.

Python module pyaml should be installed into Python:
    python -m pip install pyaml # via pip
    sudo apt install python3-yaml # via apt

### Visual Studio
    
The latest Visual Studio 2019 Community Edition should be installed.

Workload "Desktop development with C++" should be installed.

Make sure that Individual components "C++ CMake tools for Windows" and "MSVC v140 - VS 2015 C++
build tools (v14.00)" are selected.

NOTE: CMake and Ninja required to build this project will be used from Visual Studio installation.

### Cygwin or MinGW (Git Bash)

One of these Unix-style command-line environments is required to run the build scripts.

---------------------------------------------------------------------------------------------------
## How to build and run

ATTENTION: Building the Client may take from a few minutes to an hour or more, depending on the
workstation. A multi-core i7, i9 or equivalent with 32 GB or more RAM, and an SSD with 50 GB of
free space is recommended.

Open a Unix-style command line (Cygwin or Git Bash). Navigate to the directory where this readme.md
is located. Run the following commands:

./build.sh

    This will run CMake configuration and then run the build process. The build directory will
    be generated one level higher than the current directory, and will be named
    `nx-open-build-windows_x64` on Windows, and `nx-open-build-linux_x64` on Linux.
    
    ATTENTION: If the build fails, it is recommended to manually delete the build directory to
    produce a clean build, though incremental build can be attempted in certain cases.
    
Linux:    
./run.sh

Windows:
./run.bat

    This will run the Client.
    
Refer to the source code of the above scripts to learn the details on the building procedure.
