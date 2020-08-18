#!/usr/bin/env python3

import argparse
import platform
from pathlib import Path
import subprocess
import tempfile
import os
from itertools import chain
import multiprocessing
import functools
import json
import re
from enum import Enum


class Compiler(Enum):
    CLANG = 'clang'
    GCC = 'gcc'
    MSVC = 'msvc'

    def __str__(self):
        return self.name.lower()

    def __repr__(self):
        return str(self)


EXESUFFIX = '.exe' if platform.system() == 'Windows' else ''


def msvs_coverage(tempdir, args):
    # Binaries to instrument
    binaries = [b[0] for b in args.binary]

    # Get tools path.
    vsinstr = next(
        path for path in Path(args.vs_install_dir).rglob('vsinstr.exe')
        if path.parent.name == 'x64')

    perf_path = Path(args.vs_install_dir).parent.parent
    if '2019' in args.vs_install_dir:
        perf_path = perf_path / 'Shared'

    vsperfcmd = next(path for path in perf_path.rglob('VSPerfCmd.exe')
                     if path.parent.name == 'x64')

    script_dir = Path(__file__).absolute().parent
    symbold_dll = next(script_dir.rglob('*.Symbols.dll'))
    converter = symbold_dll.parent / "Converter.exe"

    # Instrument all binaries
    for binary in binaries:
        subprocess.run([vsinstr, '/coverage', binary])

    tmp_coverage_file = Path(tempdir) / 'default.coverage'

    # Start monitor.
    subprocess.run(
        [
            vsperfcmd, '/start:coverage', '/WaitStart',
            f'/output:{tmp_coverage_file}'
        ],
        check=True)

    try:
        subprocess.run(args.args)
    finally:
        # Stop monitor.
        subprocess.run([vsperfcmd, '-shutdown'])

    # Covert MS binary coverage into lcov.
    subprocess.run([converter, args.output, tmp_coverage_file])


class FileCoverage:
    def __init__(self, path):
        self.path = path
        self.funcs = {}
        self.lines = {}

    def add_func(self, line, func):
        self.funcs[line] = func

    def add_line(self, line, hits):
        self.lines[line] = self.lines.get(line, 0) + hits

    def merge(self, cov):
        for line, func in cov.funcs.items():
            self.funcs[line] = func
        for line, hits in cov.lines.items():
            self.lines[line] = self.lines.get(line, 0) + hits


class Coverage:
    def __init__(self):
        self.files = {}

    def file_coverage(self, name):
        coverage = self.files.get(name, FileCoverage(name))
        self.files[name] = coverage
        return coverage

    def append_gcov(self, path, build_dir):
        with open(path) as f:
            lines = [line.rstrip() for line in f]
        current_file = None
        for line in lines:
            if line.startswith('file:'):
                source = (build_dir / line[5:]).resolve().absolute()
                current_file = self.file_coverage(source)
            elif line.startswith('function:'):
                data = line[9:].split(',', 4)
                current_file.add_func(line=int(data[0]), func=data[3])
            elif line.startswith('lcount:'):
                data = line[7:].split(',', 3)
                current_file.add_line(line=int(data[0]), hits=int(data[1]))

    def append_gcov_json(self, data):
        for file_data in data.get('files'):
            source = file_data['file']
            current_file = self.file_coverage(source)
            for func_data in file_data.get('functions'):
                current_file.add_func(
                    line=func_data.get('start_line'), func=func_data.get('name'))
            for line_data in file_data.get('lines'):
                current_file.add_line(
                    line=line_data.get('line_number'), hits=line_data.get('count'))

    def merge(self, coverage):
        for source, cov in coverage.files.items():
            orig_cov = self.file_coverage(source)
            orig_cov.merge(cov)
        return self

    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            for source, file in self.files.items():
                print(f'SF:{source}', file=f)
                for line in sorted(file.funcs.keys()):
                    print(f'FN:{line},{file.funcs[line]}', file=f)
                line_hit = 0
                for line in sorted(file.lines.keys()):
                    if file.lines[line] > 0:
                        line_hit += 1
                    print(f'DA:{line},{file.lines[line]}', file=f)
                print(f'LH:{line_hit}', file=f)
                print(f'LF:{len(file.lines.keys())}', file=f)
                print('end_of_record', file=f)

# For multiprocessing run_gcov_text and run_gcov_json functions must be at top level


def run_gcov_text(gcov_path, dirname, gcda_files, build_dir):
    subprocess.run([gcov_path, '-i'] + gcda_files, cwd=dirname,
                   stdout=subprocess.DEVNULL, check=True)
    result = Coverage()
    for gcov_file in [str(dirname / f)+'.gcov' for f in gcda_files]:
        result.append_gcov(gcov_file, build_dir)
    return result


def run_gcov_json(gcov_path, dirname, gcda_files, build_dir):
    ret = subprocess.run([gcov_path, '--json-format', '--stdout'] + gcda_files,
                         cwd=dirname, stdout=subprocess.PIPE, check=True)

    data = json.loads(ret.stdout.decode('utf-8'))

    result = Coverage()
    result.append_gcov_json(data)
    return result


def get_gcov_version(gcov):
    result = subprocess.run([gcov, '-v'], capture_output=True, check=True)
    output = result.stdout.decode('utf-8')
    # Version is at the end of the first line of the output.
    first_line = output.split('\n', maxsplit=1)[0]
    return tuple(map(int, first_line.split()[-1].split('.')))


def get_tool_prefix(cmake_cache_file):
    r = re.compile(
        f'(?:CMAKE_AR|CMAKE_C_COMPILER_AR):FILEPATH=(.+)?ar{re.escape(EXESUFFIX)}$')

    # For llvm the tool is called llvm-ar, so avoid including llvm- into prefix.
    def strip_llvm(s): return s[:-5] if s.endswith('/llvm-') else s

    with open(cmake_cache_file, 'r') as f:
        return strip_llvm(next((m.group(1) for m in map(r.search, f) if m), ''))


def find_parent_dir(path, file):
    root = Path(path.root).resolve()
    # Let's hope no one compiles at root directory.
    while path.resolve() != root:
        if Path(path / file).exists():
            return path
        path = path.parent


def gcc_coverage(tempdir, args):
    # Coverage for each process should go to its own directory.
    gcov_env = os.environ.copy()
    gcov_env['GCOV_PREFIX'] = str(Path(tempdir) / 'cov-%p')

    subprocess.run(args.args, env=gcov_env)

    build_dir = None

    # Iterate over all process directories and
    # symlink *.gcno files near *.gcda files.
    for dirname in Path(tempdir).glob('cov-*'):
        strip_len = len(str(dirname))
        for path in dirname.rglob('*.gcda'):
            # Strip GCOV_PREFIX and get the path to .gcno file.
            gcno_file = Path(str(path)[strip_len:]).with_suffix('.gcno')
            gcno_link = path.with_suffix('.gcno')
            if not gcno_link.exists():
                gcno_link.symlink_to(gcno_file)
            build_dir = build_dir or find_parent_dir(
                gcno_file, file='CMakeCache.txt')

    # Get GCOV path.
    gcov = args.gcov or get_tool_prefix(
        build_dir / 'CMakeCache.txt') + f'gcov{EXESUFFIX}'

    # Need at least gcov 7.1.0 because of bug not allowing -i in conjunction with multiple files.
    # See: https://github.com/gcc-mirror/gcc/commit/41da7513d5aaaff3a5651b40edeccc1e32ea785a

    gcov_version = get_gcov_version(gcov)
    if gcov_version < (7, 1, 0):
        raise NotImplementedError(f'GCOV version {gcov_version}')

    # Gather dirs with their *.gcda files for multiprocessing with gcov
    dirs_gcda = []
    for dirname, _, files in os.walk(tempdir):
        gcda_files = [f for f in files if f.endswith('.gcda')]
        if gcda_files:
            dirs_gcda.append((gcov, Path(dirname), gcda_files, build_dir))

    # Intermediate format has changed in GCC 9.
    run_gcov = run_gcov_text if gcov_version < (9, 0, 0) else run_gcov_json

    # Generage and parse *.gcov in each directory
    with multiprocessing.Pool() as pool:
        lcovs = pool.starmap(run_gcov, dirs_gcda)

    # Merge parsed data
    result = functools.reduce(lambda l1, l2: l1.merge(l2), lcovs, Coverage())

    result.save(args.output)


def llvm_coverage(tempdir, args):
    binaries = [b[0] for b in args.binary]

    def find_build_dir(path):
        return find_parent_dir(Path(path), file='CMakeCache.txt')

    # Get tools path.
    build_dir = next(d for d in map(find_build_dir, binaries) if d)
    tool_prefix = get_tool_prefix(build_dir / 'CMakeCache.txt')
    llvm_profdata = [tool_prefix + f'llvm-profdata{EXESUFFIX}']
    llvm_cov = [tool_prefix + f'llvm-cov{EXESUFFIX}']

    # Each process should write its own coverage.
    profraw = Path(tempdir) / 'coverage-%p.profraw'
    prof_env = os.environ.copy()
    prof_env['LLVM_PROFILE_FILE'] = str(profraw)

    subprocess.run(args.args, env=prof_env)

    # Gather all coverage files.
    profraw_list = list(Path(tempdir).glob('coverage-*.profraw'))

    # Merge coverage from all files and create report.
    profdata = Path(tempdir) / 'coverage.profdata'
    subprocess.run(llvm_profdata +
                   ['merge', '-sparse'] + profraw_list + ['-o', profdata])
    obj_args = list(chain.from_iterable(('-object', b) for b in binaries[1:]))
    complete = subprocess.run(
        llvm_cov + ['export', '-format=lcov',
                    f'-instr-profile={profdata}', binaries[0]] + obj_args,
        stdout=subprocess.PIPE)

    # Save LCOV data.
    with open(args.output, 'wb') as f:
        f.write(complete.stdout)


COMPILERS = {
    Compiler.MSVC: msvs_coverage,
    Compiler.GCC: gcc_coverage,
    Compiler.CLANG: llvm_coverage,
}

DEFAULT_COMPILER = {
    'Windows': Compiler.MSVC,
    'Linux': Compiler.GCC,
    'Darwin': Compiler.CLANG,
}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', metavar='FILE', type=str,
                        default='lcov.info',
                        help='Write coverage info to file.')

    if platform.system() == 'Windows':
        # TODO: Autodetect from CMakeCache.txt.
        parser.add_argument(
            '--vs-install-dir', metavar='PATH', type=str,
            default='C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community',
            help='Path to Visual Studio install directory.')

    parser.add_argument('--gcov', metavar='PATH', type=str,
                        default=None,  # Autodetect from CMakeCache.txt.
                        help='Path to GCOV executable (for GCC only).')

    parser.add_argument('-b', '--binary', type=str, action='append', nargs=1, default=[],
                        help='Get coverage information for specified executable or library')

    parser.add_argument('-c', '--compiler', type=Compiler, choices=list(Compiler),
                        default=DEFAULT_COMPILER.get(platform.system()),
                        help='Specify compiler type.')

    parser.add_argument('args', nargs='+',
                        help='Launch program with arguments')

    args = parser.parse_args()

    with tempfile.TemporaryDirectory(suffix='-coverage') as tempdir:
        COMPILERS.get(args.compiler)(tempdir, args)
