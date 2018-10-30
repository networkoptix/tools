#!/usr/bin/env python3

import argparse
import os
import tempfile
import yaml

from aiohttp import web
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


def sign_binary(customization, trusted_timestamping, target_file):
    default_config_file = os.path.join(certs_directory, CONFIG_NAME)
    with open(default_config_file, 'r') as f:
        default_config = yaml.load(f)

    signing_path = os.path.join(certs_directory, customization)
    config_file = os.path.join(signing_path, CONFIG_NAME)
    with open(config_file, 'r') as f:
        config = yaml.load(f)

    def option(name):
        return config.get(name, default_config.get(name))

    timestamp_server = None
    if trusted_timestamping:
        timestamp_server = option('timestamp_server')
        print('Using trusted timestamping server {0}'.format(timestamp_server))

    if option('software'):
        certificate = os.path.join(signing_path, option('file'))
        sign_password = option('password')
        print('Using certificate {0}'.format(certificate))
        sign_software(
            signtool_directory=signtool_directory,
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server)
    else:
        print('Using hardware key')
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
    print('======== Signing {} ========'.format(filename))

    target_file = tempfile.NamedTemporaryFile(prefix=filename, suffix='.exe', delete=False)
    target_file_name = target_file.name
    while True:
        chunk = await field.read_chunk()  # 8192 bytes by default.
        if not chunk:
            break
        target_file.write(chunk)
    target_file.close()

    params = request.query
    customization = params['customization']
    trusted_timestamping = (params['trusted_timestamping'].lower() == 'true')
    print('Signing {0} with customization {1} {2}'.format(
        target_file_name,
        customization,
        '(trusted)' if trusted_timestamping else '(no timestamp)'))

    sign_binary(
        customization=customization,
        trusted_timestamping=trusted_timestamping,
        target_file=target_file_name)
    content = open(target_file_name, 'rb')
    return web.Response(body=content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certs', help='Certificates directory')
    parser.add_argument('-s', '--signtool', help='Signtool directory')
    args = parser.parse_args()

    if args.signtool:
        global signtool_directory
        signtool_directory = args.signtool
    print('Using {} as a signtool folder'.format(signtool_directory))

    if args.certs:
        global certs_directory
        certs_directory = args.certs
    print('Using {} as a certificates directory'.format(certs_directory))

    app = web.Application()
    app.add_routes([web.post('/', sign_handler)])
    web.run_app(app)


if __name__ == '__main__':
    main()
