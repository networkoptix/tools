#!/usr/bin/env python3

import argparse
import os
import subprocess
import tempfile
import yaml

from aiohttp import web
from datetime import datetime
from signtool_interface import sign_software, sign_hardware

certs_directory = os.getcwd()
signtool_directory = os.getcwd()
CONFIG_NAME = 'config.yaml'

'''
Sample config may look like:

software: True
file: 'app.p12'
password: 'qweasd123'
timestamp_server: 'http://timestamp.comodoca.com/rfc3161'

In case of hardware signing, file is not needed.
'''


def log(line):
    print('{}: {}'.format(str(datetime.now()), line))


def sign_binary(customization, trusted_timestamping, target_file):
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
        timestamp_server = config.get('timestamp_server')
        log('Using trusted timestamping server {0}'.format(timestamp_server))

    if config.get('software'):
        certificate = os.path.join(signing_path, config.get('file'))
        sign_password = config.get('password')
        log('Using certificate {0}'.format(certificate))
        sign_software(
            signtool_directory=signtool_directory,
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server)
    else:
        log('Using hardware key')
        sign_hardware(
            signtool_directory=signtool_directory,
            target_file=target_file,
            timestamp_server=timestamp_server)


async def sign_handler(request):
    reader = await request.multipart()

    field = await reader.next()
    assert field.name == 'file'
    source_filename = field.filename
    source_path, filename = os.path.split(source_filename)
    log('======== Signing {} ========'.format(filename))

    with tempfile.NamedTemporaryFile(prefix=filename, suffix='.exe', delete=False) as target_file:
        target_file_name = target_file.name
        while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:
                break
            target_file.write(chunk)

    params = request.query
    customization = params['customization']
    trusted_timestamping = (params['trusted_timestamping'].lower() == 'true')
    log('Signing {0} with customization {1} {2}'.format(
        target_file_name,
        customization,
        '(trusted)' if trusted_timestamping else '(no timestamp)'))

    try:
        sign_binary(
            customization=customization,
            trusted_timestamping=trusted_timestamping,
            target_file=target_file_name)
        content = open(target_file_name, 'rb')
        return web.Response(body=content)
    except FileNotFoundError as e:
        return web.Response(status=418, text=str(e))
    except subprocess.CalledProcessError as e:
        return web.Response(status=418, text="{}\n{}".format(e, e.output))
    except Exception as e:
        print(repr(e))
        return web.Response(status=418, text=str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certs', help='Certificates directory')
    parser.add_argument('-s', '--signtool', help='Signtool directory')
    parser.add_argument('-n', '--host', help='Host to listen')
    parser.add_argument('-p', '--port', help='Port to listen')
    args = parser.parse_args()

    if args.signtool:
        global signtool_directory
        signtool_directory = args.signtool
    log('Using {} as a signtool folder'.format(signtool_directory))

    if args.certs:
        global certs_directory
        certs_directory = args.certs
    log('Using {} as a certificates directory'.format(certs_directory))
    log('Using {} as a temporary directory'.format(tempfile.gettempdir()))

    app = web.Application()
    app.add_routes([web.post('/', sign_handler)])
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
