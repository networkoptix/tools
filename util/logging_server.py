#!/usr/bin/env python3

import argparse
import logging
import logging.config
import os
from pathlib import Path
import yaml

from aiohttp import web


async def log_handler(request):
    try:
        logging.info(f"---------- Received {request.method} request on {request.path} -----------")
        params = request.query.items()
        if len(params) > 0:
            logging.info("Query params:\n" + "\n".join([f"'{k}': '{v}'" for k, v in params]))
        if request.can_read_body:
            data = await request.content.read()
            logging.info("Data:")
            logging.info(data)
    except Exception as e:
        logging.warning("{}\n{}".format(repr(e), str(e)))

    return web.Response(text="Request logged successfully")


def main():
    with open(Path(os.path.realpath(__file__)).parent / 'logging_server_config.yaml', 'r') as f:
        log_config = yaml.load(f)
        log_config["handlers"]["file"]["filename"] = os.path.expandvars(
            log_config["handlers"]["file"]["filename"])
        logging.config.dictConfig(log_config)

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--host', help='Host to listen')
    parser.add_argument('-p', '--port', help='Port to listen')
    args = parser.parse_args()

    logging.info('------------------------------ Process started ------------------------------')

    app = web.Application()
    app.add_routes([web.route('*', '/{tail:.*}', log_handler)])
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
