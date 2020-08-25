#!/usr/bin/env python3

import argparse
import asyncio
import base64
from dataclasses import dataclass
import logging
import logging.config
import os
import tempfile
import yaml

from aiohttp import web
from pathlib import Path

FAILED_SIGNING_CODE = 418

private_key = None


@dataclass
class ExecuteCommandResult:
    stdout: bytes
    stderr: bytes
    returncode: int

    def __str__(self):
        text = str(self.returncode)
        if self.stdout:
            text += '\n' + self.stdout.decode().strip()
        if self.stderr:
            text += '\n' + self.stderr.decode().strip()
        return text


async def execute_command_async(command):
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await process.communicate()
    return ExecuteCommandResult(stdout, stderr, process.returncode)


async def sign(target_file):
    command = ['openssl', 'dgst', '-sha256', '-sign', private_key, target_file]
    return await execute_command_async(command)


async def sign_handler(request):
    reader = await request.multipart()

    field = await reader.next()
    assert field.name == 'file'
    source_filename = field.filename
    source_path, filename = os.path.split(source_filename)
    logging.info('======== Signing {} ========'.format(filename))
    filename, extension = os.path.splitext(filename)

    with tempfile.NamedTemporaryFile(prefix=filename,
                                     suffix=extension,
                                     delete=False) as target_file:
        target_file_name = target_file.name
        while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:
                break
            target_file.write(chunk)

    logging.info('Signing {0}'.format(target_file_name))

    async def complete_response(response):
        await response.prepare(request)
        await response.write_eof()
        os.remove(target_file_name)
        return response

    try:
        process_result = await sign(target_file=target_file_name)
        if process_result.returncode == 0:
            signature = base64.b64encode(process_result.stdout).decode('utf-8')
            logging.info('Signing complete\n{}'.format(signature))
            logging.info('================')
            return await complete_response(web.Response(text=signature))

        diagnostics = str(process_result)

    except Exception as e:
        diagnostics = "{}\n{}".format(repr(e), str(e))

    logging.warning('Signing failed: {}'.format(diagnostics))
    logging.warning('================')
    return await complete_response(web.Response(status=FAILED_SIGNING_CODE, text=diagnostics))


def main():
    with open(Path(os.path.realpath(__file__)).parent / 'log_config.yaml', 'r') as f:
        log_config = yaml.load(f)
        log_config['handlers']['file']['filename'] = os.path.expandvars(
            log_config['handlers']['file']['filename'])
        logging.config.dictConfig(log_config)

    parser = argparse.ArgumentParser()
    parser.add_argument('-k', '--key', help='Private key', required=True)
    parser.add_argument('-n', '--host', help='Host to listen')
    parser.add_argument('-p', '--port', help='Port to listen', default=8081)
    args = parser.parse_args()

    global private_key
    private_key = args.key

    if not Path(private_key).exists():
        logging.critical('Private key {} does not exists'.format(private_key))
        exit(1)

    logging.info('------------------------------ Process started ------------------------------')
    logging.info('Private key: {}'.format(private_key))
    logging.info('Using {} as a temporary directory'.format(tempfile.gettempdir()))

    app = web.Application()
    app.add_routes([web.post('/', sign_handler)])

    # ProactorEventLoop is required to run async subprocesses in windows.
    asyncio.set_event_loop(asyncio.ProactorEventLoop())
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
