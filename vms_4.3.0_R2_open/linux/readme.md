# Network Optix VMS Desktop Client build package

This directory contains the package of source code and pre-built third-party artifacts needed to
build the Network Optix VMS Desktop Client for Linux x64.

---------------------------------------------------------------------------------------------------
## Legal notice

The whole contents of this package is considered proprietary to Network Optix, except for the
particular files licensed by third parties under one of the open-source licenses.

The product built from this package is intended for technical experiments only, and must not be
used by end users as part of a Video Management System (VMS).

---------------------------------------------------------------------------------------------------
## General information

Commit: 178db5269af5
Customization: MetaVMS
Version: 4.3.0
Meta-version: R2-OPEN

The built Client can connect to the corresponding MetaVMS Server 4.3.0 R2.

Building of the .deb distribution is not supported by this package.

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

Building of this package has been tested on Ubuntu 18.04. Other versions/flavors may work as well.

### Python

Python 3.8+ should be installed and available on PATH as `python`.

Python module pyaml should be installed into Python using either one of the following methods:
    python -m pip install pyaml #< via pip
    sudo apt install python3-yaml #< via apt

### Cmake

CMake 3.19.0 or higher should be installed and available on PATH.

### Ninja

Ninja 1.8.0 or higher should be installed and available on PATH:
    sudo apt install ninja-build


### Other requirements

Package "pkg-config" should be installed:
   sudo apt install pkg-config

---------------------------------------------------------------------------------------------------
## How to build and run

ATTENTION: Building the Client may take from a few minutes to an hour or more, depending on the
workstation. A multi-core i7, i9 or equivalent with 32 GB or more RAM, and an SSD with 50 GB of
free space is recommended.

Open a terminal and navigate to the directory where this readme.md is located. Run the following
commands:

./build.sh

    This will run CMake configuration and then run the build process. The build directory will
    be created one level higher than the current directory, and will be named
    `vms_4.3.0_R2_OPEN_linux_x64-build`.
    
    ATTENTION: If the build fails, it is recommended to manually delete the build directory to
    produce a clean build, though incremental build can be attempted in certain cases.
      
./run.sh

    This will run the built Client.
    
Refer to the source code of the above scripts to learn the details on the building procedure.
