#!/usr/bin/env python3

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

"""Process a JSON file by removing certain keys and performing case-sensitive replacements in them.
Both the -d and -r parameters can be specified multiple times.

Examples:

Replacing mentions of `system` with `site`:
    ./process_json.py -r system:site -- openapi_v3.json openapi_v3_processed.json

Replacing mentions of `v3` with `vX`, and removing the `description` and `summary` keys:
    ./process_json.py -d description -d summary -r v3:vX -- openapi_v3.json openapi_v3_processed.json
"""
import json
from pathlib import Path
from typing import Union, Optional


def remove_keys(data: Union[dict, list], removals: list[str]):
    if isinstance(data, dict):
        for key in removals:
            data.pop(key, None)
        for value in data.values():
            remove_keys(value, removals)
    elif isinstance(data, list):
        for item in data:
            remove_keys(item, removals)


def replace_keys(data: Union[dict, list, str], replacements: Optional[dict[str, str]] = None) -> Union[dict, list, str]:
    """
    Recursively replace substrings in dictionary keys and string items in lists.

    Args:
        data (dict, list, str): The data structure to process.
        replacements (dict, optional): A dictionary of substrings to replace with their replacements.

    Returns:
        dict, list, str: The processed data structure with replacements applied.
    """
    if replacements is None:
        return data

    if isinstance(data, dict):
        keys = list(data.keys())
        for key in keys:
            value = data[key]
            new_key = key
            for substr, replacement in replacements.items():
                if substr in new_key:
                    new_key = new_key.replace(substr, replacement)
            if new_key != key:
                if new_key in data:
                    raise ValueError(f"Conflict detected for path '{new_key}'.")
                data[new_key] = value
                del data[key]
            # Recursively process the value and assign it back
            data[new_key] = replace_keys(value, replacements)
        return data
    elif isinstance(data, list):
        for index in range(len(data)):
            item = data[index]
            replaced_item = replace_keys(item, replacements)
            data[index] = replaced_item
        return data
    elif isinstance(data, str):
        for substr, replacement in replacements.items():
            data = data.replace(substr, replacement)
        return data

    else:
        return data

def replacements_from_args(args: Optional[list[str]]) -> Optional[dict[str, str]]:
    if args is None:
        return None
    """Convert a list of "key:value" strings into a dictionary mapping keys to values."""
    return {
        key.strip(): value.strip() 
        for arg in args 
        for key, value in [arg.split(":", 1)]
    }


def save_sorted_json(data: dict, output_file: Path):
    with output_file.open("w") as fp:
        json.dump(data, fp, sort_keys=True, indent=4)


if __name__ == "__main__":
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "-d", "--delete", dest="removals", action="append", help="Keys to remove.", default=None
    )
    parser.add_argument(
        "-r",
        "--replace",
        action="append",
        dest="replacements",
        help="Specify replacements in the format pattern:text, where `pattern` is the string that "
        "should be replaced, and `text` is the string it should be replaced with.",
    )
    parser.add_argument("input", type=Path, help="Input JSON file.")
    parser.add_argument("output", type=Path, help="Output JSON file.")
    args = parser.parse_args()

    if not any((args.removals, args.replacements)):
        import sys

        print("ERROR: Please specify at least one replacement or removal.")
        sys.exit(1)

    keys_to_remove = args.removals
    replacements = replacements_from_args(args.replacements)

    data = json.load(fp=args.input.open())
    remove_keys(data, keys_to_remove)
    replace_keys(data, replacements)
    save_sorted_json(data, output_file=args.output)

