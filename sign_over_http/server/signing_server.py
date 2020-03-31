#!/usr/bin/env python3

import argparse
import asyncio
import logging
import logging.config
import os
from pathlib import Path
import random
import tempfile
import yaml

from aiohttp import web
from signtool_interface import sign_software, sign_hardware
from environment import execute_command_async

certs_directory = os.getcwd()
signtool_directory = os.getcwd()
CONFIG_NAME = 'config.yaml'

CERT_INFO_TIMEOUT = 30  # seconds
DEFAULT_SIGN_TIMEOUT = 90  # seconds

FAILED_SIGNING_CODE = 418

printed_certificates = set()

'''
Sample config may look like:

software: True
file: 'app.p12'
password: 'qweasd123'
timestamp_server: 'http://timestamp.comodoca.com/rfc3161'

In case of hardware signing, file is not needed.
'''


def prerare_diagnostics(process_result):
    text = process_result.stdout
    if process_result.stderr:
        text += '\n' + process_result.stderr
    text = text.replace('\n\n', '\n')
    return text


async def print_certificate_info(certificate, password):
    global printed_certificates
    if certificate in printed_certificates:
        return
    printed_certificates.add(certificate)

    if not os.path.exists(certificate):
        logging.warning('File {} was not found'.format(certificate))
        return

    command = ['certutil', '-dump', '-p', password, certificate]
    try:
        result = await execute_command_async(command, timeout=CERT_INFO_TIMEOUT)
        logging.info(result.stdout)
        logging.warning(result.stderr)
    except FileNotFoundError as e:
        logging.warning(e)


async def sign_binary(customization, trusted_timestamping, target_file, timeout):
    default_config_file = os.path.join(certs_directory, CONFIG_NAME)
    with open(default_config_file, 'r') as f:
        default_config = yaml.load(f)

    signing_path = os.path.join(certs_directory, customization)
    config_file = os.path.join(signing_path, CONFIG_NAME)

    config = default_config.copy()
    try:
        with open(config_file, 'r') as f:
            config.update(yaml.load(f))
    except FileNotFoundError:
        pass

    timestamp_server = None
    if trusted_timestamping:
        timestamp_servers = config.get('timestamp_servers')
        timestamp_server = random.choice(timestamp_servers)
        logging.info('Using trusted timestamping server {0}'.format(timestamp_server))

    if config.get('software'):
        certificate = os.path.join(signing_path, config.get('file'))
        sign_password = config.get('password')
        logging.info('Using certificate {0}'.format(certificate))
        await print_certificate_info(certificate, sign_password)
        return await sign_software(
            signtool_directory=signtool_directory,
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server,
            timeout=timeout)
    else:
        logging.info('Using hardware key')
        return await sign_hardware(
            signtool_directory=signtool_directory,
            target_file=target_file,
            timestamp_server=timestamp_server,
            timeout=timeout)


async def sign_handler(request):
    reader = await request.multipart()

    field = await reader.next()
    assert field.name == 'file'
    source_filename = field.filename
    source_path, filename = os.path.split(source_filename)
    logging.info('======== Signing {} ========'.format(filename))
    extension = filename[-4:]

    with tempfile.NamedTemporaryFile(prefix=filename,
                                     suffix=extension,
                                     delete=False) as target_file:
        target_file_name = target_file.name
        while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:
                break
            target_file.write(chunk)

    params = request.query
    customization = params['customization']
    trusted_timestamping = (params['trusted_timestamping'].lower() == 'true')
    sign_timeout = int(params['sign_timeout'])
    if sign_timeout <= 0:
        sign_timeout = DEFAULT_SIGN_TIMEOUT
    logging.info('Signing {0} with customization {1} {2}'.format(
        target_file_name,
        customization,
        '(trusted)' if trusted_timestamping else '(no timestamp)'))

    async def complete_response(response):
        await response.prepare(request)
        await response.write_eof()
        os.remove(target_file_name)
        return response

    try:
        result = await sign_binary(
            customization=customization,
            trusted_timestamping=trusted_timestamping,
            target_file=target_file_name,
            timeout=sign_timeout)

        if result.returncode == 0:
            logging.info('Signing complete')
            logging.info('================')
            content = open(target_file_name, 'rb')
            return await complete_response(web.Response(body=content))

        text = prerare_diagnostics(result)

    except FileNotFoundError as e:
        text = str(e)

    except Exception as e:
        text = "{}\n{}".format(repr(e), str(e))

    logging.warning('Signing failed: {}'.format(text))
    logging.warning('================')
    return await complete_response(web.Response(status=FAILED_SIGNING_CODE, text=text))


def main():
    with open(Path(os.path.realpath(__file__)).parent / 'log_config.yaml', 'r') as f:
        log_config = yaml.load(f)
        log_config["handlers"]["file"]["filename"] = os.path.expandvars(
            log_config["handlers"]["file"]["filename"])
        logging.config.dictConfig(log_config)

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certs', help='Certificates directory')
    parser.add_argument('-s', '--signtool', help='Signtool directory')
    parser.add_argument('-n', '--host', help='Host to listen')
    parser.add_argument('-p', '--port', help='Port to listen')
    args = parser.parse_args()

    logging.info('------------------------------ Process started ------------------------------')

    if args.signtool:
        global signtool_directory
        signtool_directory = os.path.abspath(args.signtool)
    logging.info('Using {} as a signtool folder'.format(signtool_directory))

    if args.certs:
        global certs_directory
        certs_directory = os.path.abspath(args.certs)
    logging.info('Using {} as a certificates directory'.format(certs_directory))
    logging.info('Using {} as a temporary directory'.format(tempfile.gettempdir()))

    app = web.Application()
    app.add_routes([web.post('/', sign_handler)])

    # ProactorEventLoop is required to run async subprocesses in windows.
    asyncio.set_event_loop(asyncio.ProactorEventLoop())
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
