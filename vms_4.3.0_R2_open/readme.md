# Preliminary Client open-source packages for Windows and Linux

This directory contains the files which make up two archives, .zip for Windows and .tgz for Linux,
that allow to build a VMS Client.

Each archive contains, in addition to the files in this repository, the folders and files from the
source repository, RDEP packages, and conan packages, listed in file_list.txt in each subdirectory.
These file_list.txt are not part of the archives.

The exact commit from which the files were taken is listed in the respective readme.md files.

The following modifications have been made to the files in the archives:

- Patched source code: each copyright notice has been stripped of the MPL mentioning, making it
    effectively proprietary-licensed.

- Patched source code: removed credentials for stats server from
    open_candidate\vms\libs\nx_vms_common\src\nx\vms\statistics\settings.h

- Patched artifacts: removed cloud hosts except Meta-related from
    packages/any/cloud_hosts/cloud_hosts.json 

NOTE: Certain artifacts included in the archives may be not needed to build a Client.

ATTENTION: This readme is private to Network Optix and is not intended to be distributed with these
archives.
