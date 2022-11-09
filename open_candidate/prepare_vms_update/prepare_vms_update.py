#!/usr/bin/env python
## Copyright 2018-present Network Optix, Inc. Licensed under MPL 2.0: www.mozilla.org/MPL/2.0/


import argparse
import base64
import hashlib
import json
import logging
import mmap
import os
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile


OPENSSL_EXECUTABLE = shutil.which("openssl")


def calculate_md5(file_name):
    logging.debug(f"Calculating md5 for {file_name}")
    with open(file_name) as file, mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as file:
        return hashlib.md5(file).hexdigest()


def sign_file(file_name, key_file):
    logging.debug(f"Signing update package {file_name} with key {key_file}")
    return base64.b64encode(subprocess.check_output([
        OPENSSL_EXECUTABLE, "dgst",
        "-sign", key_file, "-keyform", "PEM",
        "-sha256", "-binary", file_name])).decode("utf-8")


def get_file_contents(path):
    if Path(path).exists():
        with open(path) as file:
            logging.debug(f"Reading {path}")
            return file.read().strip()
        logging.debug(f"File is missing: {path}")
    return None


def gather_packages(source_dir, signature_key=None):
    source_dir = Path(source_dir)
    logging.info(f"Gathering packages in {source_dir}")

    result = {}
    version = None
    reference_package = None

    for file in source_dir.iterdir():
        if not file.is_file() or not str(file).endswith(".zip"):
            continue

        info = {}

        with ZipFile(file) as zip:
            with zip.open("package.json", "r") as package_json:
                info = json.load(package_json)
                result[file] = info

        file_version = info["version"]

        if version:
            if version != file_version:
                logging.error(f"Versions of update packages mismatch.\n"
                    "{reference_package}: {version}\n{file}: {file_version}")
                return None
        else:
            reference_package = file
            version = file_version

    for file, info in result.items():
        info["size"] = file.stat().st_size
        info["md5"] = calculate_md5(file)
        if signature_key and OPENSSL_EXECUTABLE:
            info["signature"] = sign_file(file, signature_key)
        else:
            signature_file = Path(f"{file}.sig")
            if signature_file.exists():
                info["signature"] = get_file_contents(signature_file)

    return result


def make_packages_json(source_dir, packages):
    if not packages:
        return None

    first_package_info = next(iter(packages.values()))

    packages_json = {
        "version": first_package_info["version"],
        "cloudHost": first_package_info["cloudHost"],
    }

    source_dir = Path(source_dir)

    if release_notes_url := get_file_contents(source_dir / "release_notes_url.txt"):
        packages_json["releaseNotesUrl"] = release_notes_url
    if description := get_file_contents(source_dir / "description.txt"):
        packages_json["description"] = description
    if eula := get_file_contents(source_dir / "eula.html"):
        packages_json["eula"] = eula
    if eula_version := get_file_contents(source_dir / "eula_version.txt"):
        packages_json["eulaVersion"] = eula_version

    package_list = []
    for file, info in packages.items():
        package = {
            "file": file.name,
            "component": info["component"],
            "platform": info["platform"],
            "variants": info["variants"],
            "size": info["size"],
            "md5": info["md5"],
            "signature": info.get("signature", ""),
        }

        package_list.append(package)

    packages_json["packages"] = package_list

    return packages_json


def make_output_dir(source_dir, output_dir_base, packages_json):
    source_dir = Path(source_dir)
    output_dir = Path(output_dir_base) / packages_json["version"]
    logging.info(f"Generating output directory: {output_dir}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    for package in packages_json["packages"]:
        logging.info(f"Copying {package['file']}")
        shutil.copy2(source_dir / package["file"], output_dir)

    logging.info(f"Saving {output_dir / 'packages.json'}")
    with open(output_dir / "packages.json", "w") as json_file:
        json.dump(packages_json, json_file, indent=2)


def main():
    logging.basicConfig(
        level=os.getenv("PREPARE_VMS_UPDATE_LOG_LEVEL", "INFO"), format='%(message)s')

    parser = argparse.ArgumentParser(
        # formatter_class=argparse.RawTextHelpFormatter,
        description="Prepare VMS update directory for publication",
        epilog="The program collects all update ZIP files from the source directory and generates "
            "the description file packages.json. It is possible to sign the update files if "
            "a signature private key is provided. See `--signature-key`. The program also reads "
            "a number of additional files to fill packages.json with additional info when "
            "needed. "
            "\"description.txt\" contains a text which will be shown in the updates form of the "
            "VMS client after selecting the version to update. "
            "\"release_notes_url.txt\" contains a URL to release notes. "
            "When EULA needs to be updated, put the EULA into \"eula.html\" and a new eula "
            "version number into \"eula_version.txt\".")
    parser.add_argument("--source-dir", "-s", default=Path.cwd(),
        help="Source directory. All update ZIPs and additional files should be in this directory.")
    parser.add_argument("--output-dir", "-o", default=Path.cwd(),
        help="Output directory. The program will create a directory named as VMS version inside "
            "this directory and put all the files into it.")
    parser.add_argument("--signature-key",
        help="Sign update packages using this key. When not specified, the program will attempt "
            "to find the prepeared signatures in files named as update ZIPs with addition of "
            "\".sig\" suffix.")

    args = parser.parse_args()

    packages = gather_packages(args.source_dir, signature_key=args.signature_key)
    packages_json = make_packages_json(args.source_dir, packages)
    make_output_dir(args.source_dir, args.output_dir, packages_json)


if __name__ == "__main__":
    main()
