#!/usr/bin/env python3

import argparse
import os
import random
import subprocess
import tempfile
import yaml

from aiohttp import web
from datetime import datetime
from signtool_interface import sign_software, sign_hardware
from environment import execute_command

certs_directory = os.getcwd()
signtool_directory = os.getcwd()
log_file = None
CONFIG_NAME = 'config.yaml'

printed_certificates = set()

'''
Sample config may look like:

software: True
file: 'app.p12'
password: 'qweasd123'
timestamp_server: 'http://timestamp.comodoca.com/rfc3161'

In case of hardware signing, file is not needed.
'''


def log(line):
    message = '{}: {}'.format(str(datetime.now()), line)
    print(message)
    if log_file:
        with open(log_file, 'a+') as f:
            f.write(message + '\n')


def prerare_diagnostics(process_result):
    text = process_result.stdout
    if process_result.stderr:
        text += '\n' + process_result.stderr
    text = text.replace('\n\n', '\n')
    return text


def print_certificate_info(certificate, password):
    global printed_certificates
    if certificate in printed_certificates:
        return
    printed_certificates.add(certificate)

    if not os.path.exists(certificate):
        log('File {} was not found'.format(certificate))
        return

    command = ['certutil', '-dump', '-p', password, certificate]
    try:
        result = execute_command(command)
        log(result.stdout)
        log(result.stderr)
    except subprocess.SubprocessError as e:
        log(e)
    except FileNotFoundError as e:
        log(e)


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
        timestamp_servers = config.get('timestamp_servers')
        timestamp_server = random.choice(timestamp_servers)
        log('Using trusted timestamping server {0}'.format(timestamp_server))

    if config.get('software'):
        certificate = os.path.join(signing_path, config.get('file'))
        sign_password = config.get('password')
        log('Using certificate {0}'.format(certificate))
        print_certificate_info(certificate, sign_password)
        return sign_software(
            signtool_directory=signtool_directory,
            target_file=target_file,
            certificate=certificate,
            sign_password=sign_password,
            timestamp_server=timestamp_server)
    else:
        log('Using hardware key')
        return sign_hardware(
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
    extension = filename[-4:]

    with tempfile.NamedTemporaryFile(prefix=filename, suffix=extension, delete=False) as target_file:
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
        # Try several trusted timestamping servers in case of problems
        retries = 5 if trusted_timestamping else 1
        for try_sign in range(retries):
            result = sign_binary(
                customization=customization,
                trusted_timestamping=trusted_timestamping,
                target_file=target_file_name)
            if result.returncode == 0:
                break

        if result.returncode != 0:
            diagnostics = prerare_diagnostics(result)
            log('Signing failed!\n{}'.format(diagnostics))
            return web.Response(status=418, text=diagnostics)

        log('Signing complete')
        log('================')
        content = open(target_file_name, 'rb')
        return web.Response(body=content)
    except FileNotFoundError as e:
        log('================')
        return web.Response(status=418, text=str(e))
    except subprocess.SubprocessError as e:
        log('================')
        return web.Response(status=418, text="{}\n{}".format(e, e.output))
    except Exception as e:
        print(repr(e))
        log('================')
        return web.Response(status=418, text=str(e))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--certs', help='Certificates directory')
    parser.add_argument('-s', '--signtool', help='Signtool directory')
    parser.add_argument('-n', '--host', help='Host to listen')
    parser.add_argument('-p', '--port', help='Port to listen')
    parser.add_argument('-l', '--log', help='Additional log file')
    args = parser.parse_args()

    if args.log:
        global log_file
        log_file = args.log

    log('------------------------------ Process started ------------------------------')

    if args.signtool:
        global signtool_directory
        signtool_directory = os.path.abspath(args.signtool)
    log('Using {} as a signtool folder'.format(signtool_directory))

    if args.certs:
        global certs_directory
        certs_directory = os.path.abspath(args.certs)
    log('Using {} as a certificates directory'.format(certs_directory))
    log('Using {} as a temporary directory'.format(tempfile.gettempdir()))

    app = web.Application()
    app.add_routes([web.post('/', sign_handler)])
    web.run_app(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
