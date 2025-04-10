# Deployment Code Tool - tool for generating VMS server deployment code

// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

## Description

This tool generates a VMS server deployment code and QR Code image with the URL which includes
the deployment code without need to start the server. The generated code may be later used to
register the server on the cloud Deployment Service. After that, when the Server goes online for
the first time it will automatically be bound to the Cloud Site and be ready to use.
The tool has 3 external dependencies which must be installed via pip: `segno` - for generating
QR Codes, `passlib` for scrypt implementation and `numpy` for converting byte array to 16 bit number array
to make AlphaNum symbol distribution more even. Also it's recommended to install `scrypt`
library or use Python compiled with OpenSSL support, without any of those the execution time
might be pretty long.

## Parameters
--hwcode - VMS Server hardware code. In the most simple case it's the Server machine MAC address.
    MAC address should always be represented as `AA-BB-CC-11-22-33` string (upper case and `-` as
    a delimiter).
    Bios Id and server hardware Id  strings might be added to the MAC in case if a corresponding
    Deployment Code generation policy is set in the VMS Server configuration. The way how those
    values can be acquired are very different for each platform so to check if they are correct
    it's advised to use VMS server (!TODO TBD!) endpoint. The ones provided to this tool should be
    exactly the same. `$` should be used as a separator between MAC, bios Id and server hardware Id.
    Required.

    Examples:
    - MAC only: AA-BB-CC-11-22-33
    - MAC + BiosId: AA-BB-CC-11-22-33$N7YR4FEC19
    - MAC + BiosId + HardwareId: AA-BB-CC-11-22-33$N7YR4FEC19$D3B9BF02-2358-4515-B6E5-42C163B0BFBF

--salt - A string with the arbitrary salt. Must be the same as set in the VMS Server
    configuration. Required.

--image-file - A path to a file with the resulting QR Code image, `.png` or `.svg` extension is
    recommended.

--base-url - A base url for encoding into QR Code image. Before encoding a string
    `?deploymentCode=GeneratedCode` is appended to it.

## Examples
`deployment_code_tool.py --hwcode=00-B0-D0-63-C2-26 --salt=RandomSalt --image-file=/tmp/qrcode.png --base-url=https://cloud.com`

Generate a deployment code and write a corresponding QR Code image to the /tmp directory.
