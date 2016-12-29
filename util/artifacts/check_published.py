#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Runs through beta__builds directories tree and check if all artifacts are published
See: https://networkoptix.atlassian.net/wiki/display/SD/Installer+Filenames
"""

import sys
import argparse
import os
import requests

utilDir = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir)
sys.path.insert(0, utilDir)
from common_module import init_color,info,green,warn,err,separator
sys.path.pop(0)

from artifact import get_artifacts

verbose = False

source_path = "http://beta.networkoptix.com/beta-builds/daily/13804-prod_3.0.0/default"
samples = ["nxwitness-client-3.0.0.13804-linux86-beta-test.deb",
            "nxwitness-client-3.0.0.13804-linux86-beta.tar.gz",
            "nxwitness-client-3.0.0.13804-linux86-test.zip",
            "nxwitness-client-3.0.0.13804-linux86.msi"]
           
def check_file_exists(path):
    full_path = '/'.join([source_path, path])
    if verbose:
        info("Requesting {0}".format(full_path))
    response = requests.head(full_path)
    if verbose:
        info("Response {0}".format(response.status_code))
    return response.status_code == requests.codes.ok

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('build', type=int, help="Build number")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-c', '--color', action='store_true', help="colorized output")
    parser.add_argument('--customization', metavar="c", help="customization name (all customizations are checked if not set)")
    parser.add_argument('--cloud', metavar="cloud", default="", help="cloud instance name (default is empty)")
    parser.add_argument('-b', '--beta', action='store_true', help="beta status (default is false)")
    
    args = parser.parse_args()
    if args.color:
        init_color()

    green("Validating:\n    Customization: {0}\n    Build: {1}\n    Cloud: {2}\n    Beta: {3}".format(
        "All" if not args.customization else args.customization,
        args.build,
        args.cloud, 
        "true" if args.beta else "false"))
        
    global verbose
    verbose = args.verbose
    if verbose:
        warn("Verbose mode")
        
    return

    for s in samples:
        a = Artifact(s)
        warn(a.name)
        info(a.product)
        info(a.apptype)
        info(a.version)
        info(str(a.beta))
        info(a.cloud)
        info(a.extension)
        check_file_exists("linux/"+ a.name)

    err("OK")


if __name__ == '__main__':
    main()
    sys.exit(0)