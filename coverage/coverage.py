#!/usr/bin/env python3

import argparse
import platform
from pathlib import Path
import subprocess
import tempfile
import os
from itertools import chain
import sys
import multiprocessing
import functools
import json


def msvs_coverage(tempdir, args):
    # Binaries to instrument
    binaries = [b[0] for b in args.binary]

    vsinstr = next(path for path in Path(args.vs_install_dir).rglob('vsinstr.exe') if path.parent.name == 'x64')

    perf_path = Path(args.vs_install_dir).parent.parent
    if '2019' in args.vs_install_dir:
        perf_path = perf_path / 'Shared'

    vsperfcmd = next(path for path in perf_path.rglob('VSPerfCmd.exe') if path.parent.name == 'x64')

    converter = next(Path(__file__).absolute().parent.rglob('*.Symbols.dll')).parent / "Converter.exe"

    # Instrument all binaries
    for binary in binaries:
        subprocess.run([vsinstr, '/coverage', binary])

    tmp_coverage_file = Path(tempdir) / 'default.coverage'

    subprocess.run([vsperfcmd, '/start:coverage', '/WaitStart', f'/output:{tmp_coverage_file}'], check=True)
    try:
        subprocess.run(args.args)
    finally:
        subprocess.run([vsperfcmd, '-shutdown'])

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

class Lcov:
    def __init__(self):
        self.files = {}

    def append_gcov(self, path, build_dir):
        with open(path) as f:
            lines = [line.rstrip() for line in f]
        current_file = None
        for line in lines:
            if line.startswith('file:'):
                name = (build_dir / line[5:]).resolve().absolute()
                current_file = self.files.get(name, FileCoverage(name))
                self.files[name] = current_file
            elif line.startswith('function:'):
                data = line[9:].split(',', 4)
                current_file.add_func(line=int(data[0]), func=data[3])
            elif line.startswith('lcount:'):
                data = line[7:].split(',', 3)
                current_file.add_line(line=int(data[0]), hits=int(data[1]))

    def append_gcov_json(self, data):
        for file_data in data.get('files'):
            name = file_data['file']
            current_file = self.files.get(name, FileCoverage(name))
            self.files[name] = current_file
            for func_data in file_data.get('functions'):
                current_file.add_func(
                    line=func_data.get('start_line'), func=func_data.get('name'))
            for line_data in file_data.get('lines'):
                current_file.add_line(
                    line=line_data.get('line_number'), hits=line_data.get('count'))

    def merge(self, lcov):
        for source, cov in lcov.files.items():
            orig_cov = self.files.get(source, FileCoverage(source))
            self.files[source] = orig_cov
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
    subprocess.run([gcov_path, '-i'] + gcda_files, cwd=dirname, stdout=subprocess.DEVNULL, check=True)
    result = Lcov()
    for gcov_file in [str(dirname / f)+'.gcov' for f in gcda_files]:
        result.append_gcov(gcov_file, build_dir)
    return result

def run_gcov_json(gcov_path, dirname, gcda_files, build_dir):
    ret = subprocess.run([gcov_path, '--json-format', '--stdout'] + gcda_files,
                   cwd=dirname, stdout=subprocess.PIPE, check=True)

    data = json.loads(ret.stdout.decode('utf-8'))

    result = Lcov()
    result.append_gcov_json(data)
    return result

def get_gcov_version(gcov):
    result = subprocess.run([gcov, '-v'], capture_output=True, check=True)
    output = result.stdout.decode('utf-8')
    first_line = output.split('\n', maxsplit=1)[0]
    return tuple(map(int, first_line.split()[-1].split('.')))

def gcc_coverage(tempdir, args):
    gcov_env = os.environ.copy()
    gcov_env['GCOV_PREFIX'] = tempdir

    subprocess.run(args.args, env=gcov_env)

    build_dir = None

    def find_parent_dir(path, file):
        root = Path(path.root).resolve()
        # Let's hope no one compiles at root directory.
        while path.resolve() != root:
            if Path(path / file).exists():
                return path
            path = path.parent

    # Symlink *.gcno files near *.gcda files
    cut_len = len(tempdir)
    for path in Path(tempdir).rglob('*.gcda'):
        gcno_file = Path(str(path)[cut_len:]).with_suffix('.gcno')
        gcno_link = path.with_suffix('.gcno')
        if not gcno_link.exists():
            gcno_link.symlink_to(gcno_file)
        build_dir = build_dir or find_parent_dir(gcno_file, file='CMakeCache.txt')

    # Need at least gcov 7.1.0 because of bug not allowing -i in conjunction with multiple files
    # See: https://github.com/gcc-mirror/gcc/commit/41da7513d5aaaff3a5651b40edeccc1e32ea785a

    gcov_version = get_gcov_version(args.gcov)
    if gcov_version < (7, 1, 0):
        raise NotImplementedError(f'GCOV version {gcov_version}')

    # Gather dirs with their *.gcda files for multiprocessing with gcov
    dirs_gcda = []
    for dirname, _, files in os.walk(tempdir):
        gcda_files = [f for f in files if f.endswith('.gcda')]
        if gcda_files:
            dirs_gcda.append((args.gcov, Path(dirname), gcda_files, build_dir))

    # Intermediate format has changed in GCC 9.
    run_gcov = run_gcov_text if gcov_version < (9, 0, 0) else run_gcov_json

    # Generage and parse *.gcov in each directory
    with multiprocessing.Pool() as pool:
        lcovs = pool.starmap(run_gcov, dirs_gcda)

    # Merge parsed data
    result = functools.reduce(lambda l1, l2: l1.merge(l2), lcovs, Lcov())

    result.save(args.output)

def llvm_coverage(tempdir, args):
    binaries = [b[0] for b in args.binary]

    profraw = Path(tempdir) / 'default.profraw'
    prof_env = os.environ.copy()
    prof_env['LLVM_PROFILE_FILE'] = profraw

    subprocess.run(args.args, env=prof_env)

    profdata = Path(tempdir) / 'default.profdata'
    subprocess.run(['xcrun', 'llvm-profdata', 'merge', '-sparse', profraw, '-o', profdata])
    obj_args = list(chain.from_iterable(('-object', b) for b in binaries[1:]))
    complete = subprocess.run(
        ['xcrun', 'llvm-cov', 'export', '-format=lcov', f'-instr-profile={profdata}', binaries[0]] + obj_args,
        stdout=subprocess.PIPE)

    # Save LCOV data
    with open(args.output, 'wb') as f:
        f.write(complete.stdout)

if __name__ == '__main__':
    plat = platform.system()

    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--output', metavar='FILE', type=str,
        default='lcov.info',
        help='Write coverage info to file.')
    if plat == 'Windows':
        parser.add_argument('--vs-install-dir', metavar='PATH', type=str,
            default='C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\Community',
            help='Path to Visual Studio install directory.')
    else:
        parser.add_argument('--gcov', metavar='PATH', type=str,
            default='gcov',
            help='Path to GCOV executable (for GCC only).')

    parser.add_argument('-b', '--binary', type=str, action='append', nargs=1, default=[],
        help='Get coverage information for specified executable or library')

    parser.add_argument('args', nargs='+',
        help='Launch program with arguments')

    args = parser.parse_args()

    with tempfile.TemporaryDirectory(suffix='-coverage') as tempdir:
        if plat == 'Windows':
            msvs_coverage(tempdir, args)
        elif plat == 'Linux':
            gcc_coverage(tempdir, args)
        elif plat == 'Darwin':
            llvm_coverage(tempdir, args)
        else:
            raise Exception('Unknown platform')
