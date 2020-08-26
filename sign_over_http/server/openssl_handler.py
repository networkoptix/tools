import base64
import logging

from aiohttp import web
from environment import *

ID = 'openssl_handler'
private_key = CONFIG_PATH / ID / 'private.pem'


async def sign_file(filename, params):
    command = ['openssl', 'dgst', '-sha256', '-sign', private_key.as_posix(), filename]
    return await execute_command_async(command)


def make_response(target_file_name, process_result):
    signature = base64.b64encode(process_result.stdout).decode()
    return web.Response(text=signature)


def initialize():
    logging.info('Private key: {}'.format(private_key))
