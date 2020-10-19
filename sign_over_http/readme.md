// Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

# Overview

The **Signing server** is a web-service, intended to physically isolate all signing certificates
and private keys on a separate PC.

## Server

Service accepts HTTP POST requests on a configured socket. It requires at least python 3.7 with
`aiohttp` package installed.

Two separate signing handlers are implemented: `/signtool` (default one) and `/openssl`.

### SignTool handler

This handler uses windows-specific **signtool** utility to sign the provided `.exe` or `.msi` file.
Certificates are customization-dependent and stored privately on the server.

Request must contain multipart-encoded file body and an obligatory `customization` query parameter,
which selects the certificate. Trusted timestamping can be requested by adding
`trusted_timestamping=true` query parameter.

Server requires `signtool` utility to be available in path. As this utility tends to hang
sometimes, `sign_timeout` query parameter exists, allowing to shutdown the signing if it was not
finished in time. Value in seconds. If not passed, default timeout of 90 seconds is used.

If the signing was successful, signed file is returned as a http response. Otherwise http code 418
is returned, and http response contains the error text.

### OpenSSL handler

This handler uses **openssl** utility to generate a signature for the provided file. Private key
is stored on the server, public key is uploaded as the RDep package `update_verification_keys`.

Request must contain multipart-encoded file body.

Server requires `openssl` binary to be available in path.

If the signing was successful, signature is returned as a http response. Otherwise http code 418
is returned, and http response contains the error text.

## Client

Client-side signing scripts are developed here to be consistent with the server. They are copied
to the main Nx repository to the corresponding branches.

These scripts allow to sign a file or generate a signature using the provided server. All server
parameters are configurable. Http request timeout and retries count also supported.
