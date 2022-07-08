import logging
import os
import random
import yaml

from aiohttp import web
from environment import *
from signtool_interface import sign_software, sign_hardware

ID = 'signtool_handler'
CERT_INFO_TIMEOUT_SEC = 30
DEFAULT_SIGN_TIMEOUT_SEC = 90
CONFIG_NAME = 'config.yaml'

certs_directory = CONFIG_PATH / ID
default_config_file = certs_directory / CONFIG_NAME

printed_certificates = set()


async def print_certificate_info(certificate, password):
    global printed_certificates
    if certificate in printed_certificates:
        return
    printed_certificates.add(certificate)

    if not os.path.exists(certificate):
        logging.warning(f'Certificate file {certificate} was not found')
        return

    command = ['certutil', '-dump', '-p', password, certificate]
    process_result = await execute_command_async(command, timeout_sec=CERT_INFO_TIMEOUT_SEC)
    if process_result.success():
        logging.info(process_result.stdout.decode().strip())
    else:
        logging.warning(str(process_result))


async def sign_binary(customization, trusted_timestamping, target_file, timeout_sec):
    logging.info(f'Signing {target_file} with customization {customization}' +
        ' (trusted)' if trusted_timestamping else ' (no timestamp)')

    default_config_file = os.path.join(certs_directory, CONFIG_NAME)
    with open(default_config_file, 'r') as f:
        default_config = yaml.safe_load(f)

    signing_path = os.path.join(certs_directory, customization)
    config_file = os.path.join(signing_path, CONFIG_NAME)

    config = default_config.copy()
    try:
        with open(config_file, 'r') as f:
            config.update(yaml.safe_load(f))
    except FileNotFoundError:
        pass

    timestamp_server = None
    if trusted_timestamping:
        timestamp_servers = config.get('timestamp_servers')
        timestamp_server = random.choice(timestamp_servers)
        logging.info(f'Using trusted timestamping server {timestamp_server}')

    if config.get('software'):
        certificate = os.path.join(signing_path, config.get('file'))
        sign_password = config.get('password')
        logging.info(f'Using certificate {certificate}')
        await print_certificate_info(certificate, sign_password)
        return await sign_software(
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server,
            timeout_sec=timeout_sec)
    else:
        logging.info('Using hardware key')
        return await sign_hardware(
            target_file=target_file,
            timestamp_server=timestamp_server,
            timeout_sec=timeout_sec)


async def sign_file(filename, params):
    customization = params['customization']
    trusted_timestamping = (params['trusted_timestamping'].lower() == 'true')
    sign_timeout = (int(params['sign_timeout'])
                    if 'sign_timeout' in params
                    else DEFAULT_SIGN_TIMEOUT_SEC)
    return await sign_binary(
        customization=customization,
        trusted_timestamping=trusted_timestamping,
        target_file=filename,
        timeout_sec=sign_timeout)


def make_response(target_file_name, process_result):
    content = open(target_file_name, 'rb')
    return web.Response(body=content)


def initialize():
    assert(default_config_file.exists())
    logging.info(f'Using certificates config {default_config_file}')
