# Overview

The **windows signing server** is a web-service, intended to physically isolate all signing
certificates (both software and hardware) on a separate PC.

## Server

Service accepts HTTP POST requests on a configured socket. Request must contain multipart-encoded
file body and an obligatory `customization` query parameter, which selects the certificate.
Trusted timestamping can be requested by adding `trusted_timestamping=true` query parameter.

Server requires **signtool** utility to work with the sertificates. As this utility tends to hang
sometimes, `sign_timeout` query parameter exists, allowing to shutdown the signing if it was not
finished in time. Value in seconds. If not passed, default timeout of 90 seconds is used.

If the signing was successful, signed file is returned as a http response. Otherwise http code 418
is returned, and http response contains the error text.

Server script requires at least python 3.7 with `aiohttp` package installed.

## Client

Client-side signing script is developed here to be consistent with the server. Then client script
is copied to the main Nx repository to the corresponding branches.

This script allows to sign a file using target server. All server parameters are configurable, as
well as some useful client-side options: http request timeout and retries count.

**Important:** client http request timeout must be greater than signing timeout (it's recommended
to make it at least 30 seconds longer) to avoid hanging processes overflow on the server side.
Problem here is that if client closes it's connection (e.g. by timeout), server-side signing
process is not killed by timeout but only when signing is finished.
