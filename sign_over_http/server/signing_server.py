#!/usr/bin/env python3

import argparse
import asyncio
import logging
import logging.config
import os
import tempfile
import yaml

from aiohttp import web
from environment import CONFIG_PATH

import signtool_handler
import openssl_handler

FAILED_SIGNING_CODE = 418

handlers = [signtool_handler, openssl_handler]


async def download_file(request, handler):
    reader = await request.multipart()

    field = await reader.next()
    assert field.name == 'file'
    source_filename = field.filename
    source_path, filename = os.path.split(source_filename)
    logging.info(f'======== Signing {filename} with {handler.ID} ========')
    filename, extension = os.path.splitext(filename)

    # Temporary file will be deleted when response is complete.
    with tempfile.NamedTemporaryFile(prefix=filename,
                                     suffix=extension,
                                     delete=False) as target_file:
        target_file_name = target_file.name
        while True:
            # Chunk size is 8192 bytes by default.
            chunk = await field.read_chunk()
            if not chunk:
                break
            target_file.write(chunk)
        target_file.flush()
        os.fsync(target_file.fileno())
        target_file.close()
        return target_file_name


def make_handler(handler):

    async def sign_handler(request):
        target_file_name = await download_file(request, handler)

        async def complete_response(response):
            await response.prepare(request)
            await response.write_eof()
            logging.info(f'Removing file {target_file_name}')
            os.remove(target_file_name)
            return response

        try:
            process_result = await handler.sign_file(target_file_name, request.query)

            if process_result.success():
                logging.info('Signing complete')
                logging.info('================')
                return await complete_response(
                    handler.make_response(target_file_name, process_result))

            diagnostics = str(process_result)

        except Exception as e:
            diagnostics = f"{e!r}\n{e}"

        logging.warning(f'Signing failed: {diagnostics}')
        logging.warning('================')
        return await complete_response(web.Response(status=FAILED_SIGNING_CODE, text=diagnostics))
    return sign_handler


def main():
    with open(CONFIG_PATH / 'log.yaml', 'r') as f:
        log_config = yaml.safe_load(f)
        log_config['handlers']['file']['filename'] = os.path.expandvars(
            log_config['handlers']['file']['filename'])
        logging.config.dictConfig(log_config)

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--host', help='Host to listen')
    parser.add_argument('-p', '--port', help='Port to listen', default=8080)

    args = parser.parse_args()

    logging.info('------------------------------ Process started ------------------------------')
    logging.info(f'Using {tempfile.gettempdir()} as a temporary directory')
    for handler in handlers:
        handler.initialize()

    app = web.Application()
    app.add_routes([
        web.post('/', make_handler(signtool_handler)),
        web.post('/signtool', make_handler(signtool_handler)),
        web.post('/openssl', make_handler(openssl_handler)),
    ])

    # ProactorEventLoop is required to run async subprocesses in windows.
    asyncio.set_event_loop(asyncio.ProactorEventLoop())
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
