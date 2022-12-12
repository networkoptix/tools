from pathlib import Path
import argparse
import logging
import re
from typing import Callable

class Header():
    def __init__(self, filepath) -> None:
        self.filepath = filepath
        self.direct_includes = 0
        self.transitional_includes = 0
        self.dependencies = []

    def __str__(self) -> str:
        return f"Path {self.filepath} is included {self.direct_includes} times, total {self.transitional_includes}"

    def __repr__(self) -> str:
        return self.__str__()

    def include(self, transitional: bool = False, depth: int = 0):
        DEPTH_LIMIT = 200

        # Increase number of direct and transitional includes.
        if not transitional:
            self.direct_includes += 1
        self.transitional_includes += 1
        if depth > DEPTH_LIMIT:
            raise OverflowError("Too deep include")
        for dependency in self.dependencies:
            dependency.include(transitional=True, depth=depth+1)

INCLUDE_PATTERN = re.compile('^\s*#include\s*(["<].+)[">].*$')


project_headers = {}
external_headers = {}
roots = []


def create_header_node(filepath):
    '''
    Create headers tree node
    '''
    project_headers[filepath] = Header(filepath)


def find_header_by_include(source: Path, include: str, is_relative: bool) -> Path:
    header_path = None
    if is_relative:
        header_path = (source.parent / include).resolve()
        if header_path.exists():
            return header_path
        else:
            logging.warning(f"Unknown include {include} is relative to {source}")

    for root in roots:
        if (Path(root) / include).exists():
            return (Path(root) / include).resolve()

    return None


def parse_line(line):
    result = INCLUDE_PATTERN.findall(line)
    if len(result) == 1:
        match = result[0]
        is_relative = match.startswith('"')
        return (match[1:], is_relative)
    return None


def process_headers_in_file(filepath: Path, process_header: Callable[[Header], None]):
    with open(filepath) as file:
        for line in file:
            if "#include" in line:
                include, is_relative = parse_line(line)
                if not include:
                    logging.error(f"Invalid include line\n{line}")
                    continue
                header_path = find_header_by_include(filepath, include, is_relative)
                if not header_path:  # Include is absolute and was not found.
                    if include not in external_headers:
                        external_headers[include] = 1
                    else:
                        external_headers[include] += 1
                else:
                    if header_path in project_headers:
                        process_header(project_headers[header_path])
                    else:
                        logging.error(f"Unknown header {header_path} included in {filepath}")


def process_cpp_file(filepath: Path):

    def count_direct_include(header: Header):
        header.include()

    process_headers_in_file(filepath, count_direct_include)


def process_h_file(filepath):

    if not filepath in project_headers:
        logging.error(f"File {filepath} cannot be found in headers")
        return

    current_header = project_headers[filepath]

    def add_dependency(header: Header):
        current_header.dependencies.append(header)

    process_headers_in_file(filepath, add_dependency)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("roots", nargs='+')
    args = parser.parse_args()

    global roots

    roots = args.roots

    print(roots)
    for root in roots:
        for file in Path(root).glob("**/*.h"):
            create_header_node(file)
    for root in roots:
        for file in Path(root).glob("**/*.h"):
            process_h_file(file)
    for root in roots:
        for file in Path(root).glob("**/*.cpp"):
            process_cpp_file(file)

    print("-- Global headers top --\n")
    external_headers_list = sorted(
        list(external_headers.items()),
        key=lambda x: x[1],
        reverse=True)
    print('\n'.join(str(x) for x in external_headers_list[:10]))

    print("-- Direct includes top --\n")
    project_headers_list = sorted(
        project_headers.values(),
        key=lambda x: x.direct_includes,
        reverse=True)
    print('\n'.join(str(x) for x in project_headers_list[:10]))

    print("-- Total includes top --\n")
    transitive_top_list = sorted(
        project_headers.values(),
        key=lambda x: x.transitional_includes,
        reverse=True)
    print('\n'.join(str(x) for x in transitive_top_list[:10]))


if __name__ == "__main__":
    main()
