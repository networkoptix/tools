'''
Migrate existing brazilian translations to portuguese. They are very similar, but brazilian
translators are way more quick.
'''

import argparse
import logging
from pathlib import Path
from copy_translations import migrate_file

ALLOWED_STRINGS = [
    b'<comment>',
    b'<source>',
    b'<translation>',
    b'<numerusform>',
]

ESCAPED_SYMBOLS = [
    (b'\'', b'&apos;'),
    (b'"', b'&quot;')
]

def postprocess_file(filename):
    with open(filename, 'rb') as file:
        lines = file.readlines()

    with open(filename, 'wb') as file:
        for line in lines:
            if any(string in line for string in ALLOWED_STRINGS):
                for source, target in ESCAPED_SYMBOLS:
                    line = line.replace(source, target)
            file.write(line)


def main():
    parser = argparse.ArgumentParser(description='''
This script migrates existing Braziliang translations to Portuguese file.
''')
    parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true')
    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    brazilian_files = Path('.').glob("**/*pt_BR.ts")
    for brazilian_file in brazilian_files:
        portuguese_file = Path(brazilian_file.as_posix().replace('pt_BR', 'pt_PT'))
        if not portuguese_file.exists():
            logging.critical(f"File {portuguese_file.as_posix()} does not exist")
        else:
            migrate_file(brazilian_file, portuguese_file)
            postprocess_file(portuguese_file)


if __name__ == "__main__":
    main()
