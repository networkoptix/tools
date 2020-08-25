# Overview

The **OpenSSL signing server** is a web-service, intended to physically isolate a private key
on a separate PC.

## Server

Service accepts HTTP POST requests on a configured socket. Request must contain multipart-encoded
file body.

Server requires **openssl** binary to be available in path.

If the signing was successful, signature is returned as a http response. Otherwise http code 418
is returned, and http response contains the error text.

Server script requires at least python 3.7 with `aiohttp` package installed.

## Client

Client-side signing script is developed here to be consistent with the server. Then client script
is copied to the main Nx repository to the corresponding branches.

This script allows to sign a file using target server. All server parameters are configurable, as
well as some useful client-side options: http request timeout and retries count.
