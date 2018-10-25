#!/usr/bin/env python3

import asyncio
import aiohttp
import argparse

def bool_to_str(value):
    return 'true' if value else 'false'

chunk_size = 1024 * 1024

async def sign_binary(url, file, output, customization, trusted_timestamping, hardware_signing):
    params = {
        'customization': customization,
        'trusted_timestamping': bool_to_str(trusted_timestamping),
        'hardware_signing': bool_to_str(hardware_signing)
    }

    data = aiohttp.FormData()
    data.add_field('file',
       open(file, 'rb'),
       filename=file,
       content_type='application/exe')

    async with aiohttp.ClientSession() as session:
        async with session.post(url, params=params, data=data) as resp:
            print(resp.status)
            if resp.status != 200:
                return

            with open(output, 'wb') as fd:
                while True:
                    chunk = await resp.content.read(chunk_size)
                    if not chunk:
                        break
                    fd.write(chunk)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--url', help='Signing server url', required=True)
    parser.add_argument('-f', '--file', help='Source file path', required=True)
    parser.add_argument('-o', '--output', help='Target file path', required=True)
    parser.add_argument('-c', '--customization', help='Selected customization', required=True)
    parser.add_argument('-t', '--trusted-timestamping', action='store_true', help='Trusted timestamping')
    parser.add_argument('-hw', '--hardware-signing', action='store_true', help='Sign with hardware key')
    args = parser.parse_args()

    asyncio.run(sign_binary(
        url=args.url,
        file=args.file,
        output=args.output,
        customization=args.customization,
        trusted_timestamping=args.trusted_timestamping,
        hardware_signing=args.hardware_signing))


if __name__ == '__main__':
    main()
