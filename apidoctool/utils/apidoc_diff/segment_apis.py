#!/usr/bin/env python3

# Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/

"""Dump each OpenAPI endpoint's method definition into separate JSON files, modeling the API
structure in the filesystem.

Example:

    ./segment_apis.py openapi_v4_processed.json ./6.1.0.39544/segmented_api

This will create a directory strucure with './6.1.0.39544/segmented_api' as the root, containing
directories that model the API structure, such as `/rest/v4/servers`. In the leaf directories,
individual JSON files are dumped with the relevant segment of the OpenAPI schema definition in a
file that is named after the HTTP method (e.g. get.json, post.json, etc.).
"""
import json
from pathlib import Path

def dump_endpoints(openapi_schema: dict, output_dir: Path):
    """
    Dumps each endpoint's method definition into separate JSON files, retaining the API path as
    the filesystem directory structure.

    Args:
        openapi_schema (dict): The OpenAPI schema.
        output_dir (Path): The root directory where files will be dumped.
    """
    paths = openapi_schema.get("paths", {})
    if not paths:
        print("ERROR: No 'paths' key found in the OpenAPI schema.")
        return

    for path, methods in paths.items():
        for method, details in methods.items():
            # Ensure the method is a valid HTTP method
            if method.lower() not in {"get", "post", "put", "delete", "patch", "options", "head", "trace"}:
                print(f"WARNING: Skipping unsupported method {method!r} in path {path!r}.")
                continue

            path_parts = path.strip("/").split("/")
            dir_path = output_dir.joinpath(*path_parts)

            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print(f"ERROR: Could not create directory '{dir_path}': {e}")
                continue

            # Define the filename as <method>.json (e.g., get.json)
            filename = f"{method.lower()}.json"
            file_path = dir_path / filename

            try:
                with file_path.open("w", encoding="utf-8") as f:
                    json.dump(details, f, indent=2, sort_keys=True)
                # print(f"Dumped {method.upper()} {path} to {file_path}")
            except Exception as e:
                print(f"Error writing to file {file_path!r}: {e}")

if __name__ == "__main__":
    import sys
    from argparse import ArgumentParser, RawDescriptionHelpFormatter

    parser = ArgumentParser(
        description=__doc__, formatter_class=RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the input OpenAPI JSON file."
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Directory where the endpoint JSON files will be saved."
    )
    args = parser.parse_args()

    if not args.input.is_file():
        print(f"Error: The input file {args.input!r} does not exist or is not a file.")
        sys.exit(1)

    # Load the OpenAPI schema
    try:
        with args.input.open("r", encoding="utf-8") as f:
            openapi_schema = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {args.input!r}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {args.input!r}: {e}")
        sys.exit(1)

    # Ensure output directory exists.
    try:
        args.output.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print(f"Error creating output directory {args.output!r}: {e}")
        sys.exit(1)

    # Dump the endpoints
    dump_endpoints(openapi_schema, args.output)
