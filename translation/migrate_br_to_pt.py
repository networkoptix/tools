'''
Migrate existing brazilian translations to portuguese. They are very similar, but brazilian
translators are way more quick.
'''

import logging
from pathlib import Path
from copy_translations import migrate_file


def main():
    brazilian_files = Path('.').glob("**/*pt_BR.ts")
    for brazilian_file in brazilian_files:
        portuguese_file = Path(brazilian_file.as_posix().replace('pt_BR', 'pt_PT'))
        if not portuguese_file.exists():
            logging.critical(f"File {portuguese_file.as_posix()} does not exist")
        else:
            migrate_file(brazilian_file, portuguese_file)


if __name__ == "__main__":
    main()
