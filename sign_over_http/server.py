#!/usr/bin/env python3

import os

from tempfile import gettempdir
from aiohttp import web
import argparse
import pathlib
from signtool_interface import sign_software, sign_hardware


temp_directory = gettempdir()
certs_directory = os.getcwd()
signtool_directory = os.getcwd()
trusted_timestamping_server = 'http://timestamp.comodoca.com/rfc3161'

def certificate_path(customization):
    return os.path.join(certs_directory, customization, 'app.p12')


def sign_binary(customization, trusted_timestamping, hardware_signing, target_file):
    timestamp_server = trusted_timestamping_server if trusted_timestamping else None
    if timestamp_server:
        print('Using timestamp server {0}'.format(timestamp_server))
    if hardware_signing:
        print('Using harware key to sign {}'.format(target_file))
        sign_hardware(
            signtool_directory=signtool_directory,
            target_file=target_file,
            timestamp_server=timestamp_server)
    else:
        certificate = certificate_path(customization)
        sign_password = 'qweasd123'
        print('Using {0} to sign {1}'.format(certificate, target_file))
        sign_software(
            signtool_directory=signtool_directory,
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server)



async def sign_handler(request):
    params = request.query
    print(params['customization'])
    print(params['trusted_timestamping'])
    print(params['hardware_signing'])

    reader = await request.multipart()

    field = await reader.next()
    assert field.name == 'file'
    source_filename = field.filename
    source_path, filename = os.path.split(source_filename)
    print('filename is {}'.format(filename))

    size = 0
    target_file = os.path.join(temp_directory, filename)
    with open(target_file, 'wb') as f:
        while True:
            chunk = await field.read_chunk()  # 8192 bytes by default.
            if not chunk:
                break
            size += len(chunk)
            f.write(chunk)

    sign_binary(
        customization=params['customization'],
        trusted_timestamping=params['trusted_timestamping'].lower() == 'true',
        hardware_signing=params['hardware_signing'].lower() == 'true',
        target_file=target_file)
    content = open(target_file, 'rb')
    return web.Response(body=content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--temp', help='Temp directory')
    parser.add_argument('-c', '--certs', help='Certificates directory')
    parser.add_argument('-s', '--signtool', help='Signtool directory')
    args = parser.parse_args()

    if args.signtool:
        global signtool_directory
        signtool_directory = args.signtool
    print('Using {} as a signtool folder'.format(signtool_directory))

    if args.temp:
        global temp_directory
        temp_directory = args.temp
    print('Using {} as a temp directory'.format(temp_directory))

    if args.certs:
        global certs_directory
        certs_directory = args.certs
    print('Using {} as a certificates directory'.format(certs_directory))

    pathlib.Path(temp_directory).mkdir(parents=True, exist_ok=True)

    app = web.Application()
    app.add_routes([web.post('/', sign_handler)])
    web.run_app(app)


if __name__ == '__main__':
    main()
