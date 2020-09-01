#!/usr/bin/env python

import argparse
import sys

from generic_http_signing_client import GenericHttpSigningClient, DEFAULT_REQUEST_TIMEOUT

DEFAULT_SIGN_TIMEOUT = 90
assert DEFAULT_SIGN_TIMEOUT < DEFAULT_REQUEST_TIMEOUT


def main():
    client = GenericHttpSigningClient('signtool')

    parser = argparse.ArgumentParser()
    client.setup_common_arguments(parser)

    parser.add_argument('-c', '--customization', help='Selected customization', required=True)
    parser.add_argument(
        '-t', '--trusted-timestamping',
        action='store_true',
        help='Trusted timestamping')
    parser.add_argument(
        '--sign-timeout',
        help=f'Signing timeout in seconds ({DEFAULT_SIGN_TIMEOUT})',
        type=int,
        default=DEFAULT_SIGN_TIMEOUT)

    args = parser.parse_args()
    client.load_arguments(args)

    if client.request_timeout <= args.sign_timeout:
        print(f'ERROR: Sign timeout ({args.sign_timeout}) must be less than '
              + f'request timeout ({client.request_timeout})',
              file=sys.stderr)
        return

    params = {
        'customization': args.customization,
        'trusted_timestamping': str(args.trusted_timestamping).lower(),
        'sign_timeout': args.sign_timeout
    }

    return client.send_file(params)


if __name__ == '__main__':
    ret_code = main()
    exit(ret_code)
