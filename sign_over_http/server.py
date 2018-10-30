#!/usr/bin/env python3

import argparse
import os
import tempfile
import yaml

from aiohttp import web
from signtool_interface import sign_software, sign_hardware

certs_directory = os.getcwd()
signtool_directory = os.getcwd()
default_timestamp_server = 'http://timestamp.comodoca.com/rfc3161'


def sign_binary(customization, trusted_timestamping, target_file):
    signing_path = os.path.join(certs_directory, customization)
    config_file = os.path.join(signing_path, 'config.yaml')
    with open(config_file, 'r') as f:
        config = yaml.load(f)

    timestamp_server = None
    if trusted_timestamping:
        timestamp_server = config['timestamp_server']
        if not timestamp_server:
            timestamp_server = default_timestamp_server

    if timestamp_server:
        print('Using timestamp server {0}'.format(timestamp_server))

    if config['software']:
        certificate = os.path.join(signing_path, config['file'])
        sign_password = config['password']
        print('Using {0} to sign {1}'.format(certificate, target_file))
        sign_software(
            signtool_directory=signtool_directory,
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server)
    else:
        print('Using harware key to sign {}'.format(target_file))
        sign_hardware(
            signtool_directory=signtool_directory,
            target_file=target_file,
            timestamp_server=timestamp_server)


async def sign_handler(request):
    params = request.query
    print(params['customization'])
    print(params['trusted_timestamping'])

    reader = await request.multipart()

    field = await reader.next()
    assert field.name == 'file'
    source_filename = field.filename
    source_path, filename = os.path.split(source_filename)
    print('filename is {}'.format(filename))

    target_file = tempfile.NamedTemporaryFile(prefix=filename, suffix='.exe', delete=False)
    target_file_name = target_file.name
    while True:
        chunk = await field.read_chunk()  # 8192 bytes by default.
        if not chunk:
            break
        target_file.write(chunk)
    target_file.close()

    sign_binary(
        customization=params['customization'],
        trusted_timestamping=params['trusted_timestamping'].lower() == 'true',
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
