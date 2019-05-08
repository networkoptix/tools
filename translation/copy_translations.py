#!/usr/bin/env python

import argparse
import logging

from utils import translation


class MigrationResult:
    migrated = 0
    total = 0

    def __iadd__(self, other):
        self.migrated += other.migrated
        self.total += other.total
        return self


def migrate_context(source_context, target_context):
    result = MigrationResult()
    for text, message in target_context.messages.items():
        source_message = source_context.messages.get(text)

        if not source_message:
            logging.error("Message {0}:{1} was not found in source context".format(
                source_context.name, text))
            continue

        if message.is_numerus != source_message.is_numerus:
            logging.error("Message {0}:{1} numerus form mismatch".format(
                source_context.name, text))
            continue

        if message.is_numerus and len(message.texts) != len(source_message.texts):
            logging.error("Message {0}:{1} numerus count mismatch".format(
                source_context.name, text))
            continue

        result.total += 1
        if message.is_complete() or not source_message.is_complete():
            continue

        logging.debug("Migrating message {0}:{1}".format(
            source_context.name, text))
        message.update_from(source_message)
        result.migrated += 1

    return result


def migrate_xml(source, target):
    result = MigrationResult()
    for name, context in target.contexts.items():
        source_context = source.contexts.get(name)
        if not source_context:
            logging.error("Context {0} was not found in source file".format(name))
            continue
        result += migrate_context(source_context, context)
    return result


def migrate_file(source_path, target_path):
    logging.info("Migrating {0} from {1}".format(target_path, source_path))
    source = translation.File(source_path)
    target = translation.File(target_path)

    result = migrate_xml(source, target)
    logging.info("{0} items processed".format(result.total))
    if result.migrated > 0:
        logging.warning("{0} items migrated".format(result.migrated))
        target.flush()
    else:
        logging.debug("{0} items migrated".format(result.migrated))


def main():
    parser = argparse.ArgumentParser(description='''
This script migrates existing translations from one file to another, overriding unfinished.
''')
    parser.add_argument('-s', '--source', help="Source file", required=True)
    parser.add_argument('-t', '--target', help="Target file", required=True)
    parser.add_argument('-v', '--verbose', help="Verbose output", action='store_true')
    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level)

    migrate_file(args.source, args.target)
    logging.debug("Migration finished.")


if __name__ == "__main__":
    main()
