#!/usr/bin/env python

import argparse
import requests
import sys
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

chunk_size = 1024 * 1024

DEFAULT_REQUEST_TIMEOUT = 180
DEFAULT_RETRIES = 10


def sign_binary(
    url,
    file,
    output,
    request_timeout=DEFAULT_REQUEST_TIMEOUT,
    max_retries=DEFAULT_RETRIES
):
    last_status_code = 0
    for current_try in range(1, max_retries + 1):
        retries = Retry(
            total=max_retries,
            backoff_factor=0.1)
        session = requests.Session()
        session.mount(url, HTTPAdapter(max_retries=retries))
        try:
            with open(file, 'rb') as file_handle:
                r = session.post(url, files={'file': file_handle}, timeout=request_timeout)
            if r.status_code == 200:
                print(r.text, file=output)
                return 0
            else:
                print(f'ERROR: {r.text}', file=sys.stderr)
                last_status_code = r.status_code

        except requests.exceptions.ReadTimeout as e:
            print('ERROR: Connection to the signing server has timed out'
                  + f' ({request_timeout} seconds, {max_retries} retries) '
                  + f'while signing {file}',
                  file=sys.stderr)
            print(e)
            last_status_code = 1
        except requests.exceptions.ConnectionError as e:
            print('ERROR: Connection to the signing server cannot be established '
                  + f'while signing {file}',
                  file=sys.stderr)
            print(e)
            last_status_code = 2
        except requests.exceptions.ChunkedEncodingError as e:
            print(f'ERROR: Connection to the signing server was broken while signing {file}',
                  file=sys.stderr)
            print(e)
            last_status_code = 3
        except Exception as e:
            print(f'ERROR: Unexpected exception while signing {file}', file=sys.stderr)
            print(e)
            last_status_code = 4
        print(f'Trying to sign {file} again', file=sys.stderr)

    print(f'ERROR: Too max retries failed. Status code {last_status_code}', file=sys.stderr)
    return last_status_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Signing server url', required=True)
    parser.add_argument('-f', '--file', help='Source file path', required=True)
    parser.add_argument(
        '-o', '--output',
        help='Target signature file path. The signature will be printed to stdout if omitted.',
        type=argparse.FileType('w'),
        default='-')
    parser.add_argument(
        '--retries',
        help='Max retries count ({})'.format(DEFAULT_RETRIES),
        type=int,
        default=DEFAULT_RETRIES)
    parser.add_argument(
        '--request-timeout',
        help='Request timeout in seconds ({}). Must be greater than sign timeout'.format(
            DEFAULT_REQUEST_TIMEOUT),
        type=int,
        default=DEFAULT_REQUEST_TIMEOUT)
    args = parser.parse_args()

    actual_url = args.url + '/openssl'
    return sign_binary(
        url=actual_url,
        file=args.file,
        output=args.output,
        request_timeout=args.request_timeout,
        max_retries=args.retries)


if __name__ == '__main__':
    ret_code = main()
    exit(ret_code)
