#!/bin/env python

from __future__ import print_function
import os
import sys
import argparse
import subprocess
import shutil
import json

class QmlDeployUtil:
    def __init__(self, qt_root):
        self.qt_root = os.path.abspath(qt_root)

        self.scanner_path = QmlDeployUtil.find_qmlimportscanner(qt_root)
        if not self.scanner_path:
            print("qmlimportscanner is not found in {}".format(qt_root), file=sys.stderr)
            raise

        self.import_path = QmlDeployUtil.find_qml_import_path(qt_root)
        if not self.import_path:
            print("qml import path is not found in {}".format(qt_root), file=sys.stderr)
            raise

    def find_qmlimportscanner(qt_root):
        for name in ["qmlimportscanner", "qmlimportscanner.exe"]:
            path = os.path.join(qt_root, "bin", name)

            if os.path.exists(path):
                return path

        return None

    def find_qml_import_path(qt_root):
        path = os.path.join(qt_root, "qml")
        return path if os.path.exists(path) else None

    def invoke_qmlimportscanner(self, qml_root):
        command = [self.scanner_path, "-rootPath", qml_root, "-importPath", self.import_path]
        process = subprocess.Popen(command, stdout=subprocess.PIPE)

        if not process:
            print("Cannot start {}".format(" ".join(command)), file=sys.stderr)
            return

        return json.load(process.stdout)

    def get_qt_imports(self, imports):
        if not type(imports) is list:
            print("Parsed imports is not a list.", file=sys.stderr)
            return

        qt_deps = []

        for item in imports:
            path = item.get("path")

            if not path or os.path.commonprefix([self.qt_root, path]) != self.qt_root:
                continue

            qt_deps.append(path)

        qt_deps.sort()

        result = []
        previous_path = None

        for path in qt_deps:
            if previous_path and path.startswith(previous_path):
                continue

            result.append(path)
            previous_path = path

        return result

    def copy_components(self, paths, output_dir):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for path in paths:
            subdir = os.path.relpath(path, self.import_path)
            dst = os.path.join(output_dir, subdir)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(path, dst, symlinks=True,
                ignore = shutil.ignore_patterns("*.a", "*.prl"))

    def deploy(self, qml_root, output_dir):
        imports = self.invoke_qmlimportscanner(qml_root)
        if not imports:
            return

        paths = self.get_qt_imports(imports)
        self.copy_components(paths, output_dir)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qml-root", type=str, required=True, help="Root QML directory.")
    parser.add_argument("--qt-root", type=str, required=True, help="Qt root directory.")
    parser.add_argument("-o", "--output", type=str, required=True, help="Output directory.")

    args = parser.parse_args()

    deploy_util = QmlDeployUtil(args.qt_root)
    deploy_util.deploy(args.qml_root, args.output)

if __name__ == "__main__":
    main()
