#!/usr/bin/env python

import argparse
import requests

chunk_size = 1024 * 1024


def bool_to_str(value):
    return 'true' if value else 'false'


def sign_binary(url, file, output, customization, trusted_timestamping):

    params = {
        'customization': customization,
        'trusted_timestamping': bool_to_str(trusted_timestamping)
    }

    files = {
        'file': open(file, 'rb')
    }

    r = requests.post(url, params=params, files=files)
    if r.status_code != 200:
        print('ERROR: {}'.format(r.text))
        return r.status_code

    with open(output, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=chunk_size):
            fd.write(chunk)

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Signing server url', required=True)
    parser.add_argument('-f', '--file', help='Source file path', required=True)
    parser.add_argument(
        '-o', '--output',
        help='Target file path. Source file is replaced if omitted.')
    parser.add_argument('-c', '--customization', help='Selected customization', required=True)
    parser.add_argument(
        '-t', '--trusted-timestamping',
        action='store_true',
        help='Trusted timestamping')
    args = parser.parse_args()

    return sign_binary(
        url=args.url,
        file=args.file,
        output=args.output if args.output else args.file,
        customization=args.customization,
        trusted_timestamping=args.trusted_timestamping)


if __name__ == '__main__':
    ret_code = main()
    exit(ret_code)
