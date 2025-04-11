#!/usr/bin/env python3

## Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

"""A tool for generating VMS server deployment code"""

import argparse
import base64
import os
import sys
import segno
import numpy as np
from passlib.hash import scrypt
from pathlib import Path
from urllib.parse import urlparse

# We are using A-Z letter symbols and 2-9 digit symbols, '0' and '1' are not used
# not to confuse them with the 'O' and 'I'. 34 symbols in total which gives 34^16
# code variants.
symbol_map = {}
for i in range(0, 26):
    symbol_map[i] = chr(i + 65) #< A,B,...,Z
for i in range(26, 34):
    symbol_map[i] = chr(i + 24) #< 2,3,...,9

def to_alpha_num(int_array):
    result = ''
    for b in int_array:
        result += symbol_map[b % 34]
        if len(result) >= 16:
            break
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--hwcode",
        type=str,
        help="VMS Server hardware code. See README for details.",
        required=True)
    parser.add_argument(
        "--salt",
        type=str,
        help="Salt, same as saved in VMS Server configuration.",
        required=True)
    parser.add_argument(
        "--image-file",
        type=Path,
        help='Path to the output QR Code image file. If not provided, image won\'t be generated.')
    parser.add_argument(
        "--base-url",
        type=str,
        help=(
            "Base url for the QR Code, for example https://my-cloud.com. If not provided, "
            "image won\'t be generated."))

    args = parser.parse_args()
    hash = scrypt.using(salt=args.salt.encode()).using(rounds=10).using(parallelism=16).hash(args.hwcode)
    hash_obj = scrypt.from_string(hash)

    # Converting byte array to 16bit numbers array to make symbol distribution more even
    int_array = np.frombuffer(hash_obj.checksum, dtype=np.dtype('<u2'))
    alpha_num_code = to_alpha_num(int_array)
    print(alpha_num_code)

    if args.image_file is not None:
        if args.base_url is None:
            sys.exit("base-url is invalid")
        else:
            url_tokens = urlparse(args.base_url)
            if not all((url_tokens.scheme, url_tokens.netloc)):
                sys.exit("base-url is invalid")
            else:
                segno.make(args.base_url +'?deploymentCode=' + alpha_num_code).save(args.image_file)

if __name__ == "__main__":
    main()
