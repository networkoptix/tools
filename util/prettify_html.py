#!/usr/bin/env python3

import argparse
import sys
from bs4 import BeautifulSoup


def prettify(infile, outfile):
    source = infile.read()
    soup = BeautifulSoup(source, 'html.parser')
    outfile.write(soup.prettify())
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)
    parser.add_argument(
        'outfile',
        nargs='?',
        type=argparse.FileType('w', encoding='utf-8'),
        default=sys.stdout)
    args = parser.parse_args()
    return prettify(args.infile, args.outfile)


if __name__ == "__main__":
    if not main():
        exit(1)
