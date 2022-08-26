#!/usr/bin/env python

import asyncio
import websockets
import logging
import ssl

# VMS Endpoint.
ENDPOINT = 'wss://localhost:7001/jsonrpc'

# VMS auth session.
HEADERS = {
    'Authorization': 'Bearer vms-000000008aeb7d562bc767afae00335c-rmrknPEl6W'
}

# Requests to execute.
REQS = [
    # GET /rest/v2/servers
    '{"jsonrpc": "2.0", "method": "rest.v2.servers.list", "params": {"_with": "id,name"}, "id": 1}',
    # GET /rest/v2/system/info
    #'{"jsonrpc": "2.0", "method": "rest.v2.system.info.get", "params": {}, "id": 42}',
    # GET /rest/v2/servers/this/info
    #'{"jsonrpc": "2.0", "method": "rest.v2.servers.info.get", "params": {"id": "this"}, "id": 43}',
    # PATCH /rest/v2/servers/this -> {"name": "S1"}
    #'{"jsonrpc": "2.0", "method": "rest.v2.servers.update", "params": {"id": "this", "name": "S1"}, "id": 77}',
    # GET /rest/v2/servers/this?_with=id,name
    #'{"jsonrpc": "2.0", "method": "rest.v2.servers.get", "params": {"id": "this", "_with": "id,name"}, "id": 777}',
]

#logging.basicConfig()
#logging.getLogger().setLevel(logging.DEBUG)

async def json_rpc_test():
    # Disable SSL cert chekcs
    ssl_ctx = ssl.SSLContext()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    # Connect WebSocket to JSON-RPC
    async with websockets.connect(ENDPOINT, extra_headers=HEADERS, ssl=ssl_ctx) as ws:
        for req in REQS:
            print('\n> {}\n'.format(req))
            await ws.send(req)
            rest = await ws.recv()
            print('\n< {}\n'.format(rest))

asyncio.get_event_loop().run_until_complete(json_rpc_test())
