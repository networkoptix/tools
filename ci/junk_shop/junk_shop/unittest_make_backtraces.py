#!/usr/bin/env python
import argparse
import logging
from pathlib2 import Path
from junk_shop.unittest.make_backtraces import make_backtraces


def setup_logging(level=None):
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=level or logging.INFO, format=format)


def main():
    parser = argparse.ArgumentParser(
        usage='%(prog)s [options]')
    parser.add_argument(
        '--windows', action='store_true',
        help="Make windows backtraces.")
    parser.add_argument(
        '--work-dir', required=True,
        help='Unittests working directory')
    args = parser.parse_args()
    setup_logging()
    make_backtraces(Path(args.work_dir), args.windows)


if __name__ == "__main__":
    main()
