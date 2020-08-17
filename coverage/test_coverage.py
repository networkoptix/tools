import unittest
import subprocess
import tempfile
import platform
from pathlib import Path
import sys
import shlex


def shell_join(args):
    if platform.system() == 'Windows':
        return subprocess.list2cmdline(args)

    return ' '.join(shlex.quote(str(arg)) for arg in args)


class TestStringMethods(unittest.TestCase):

    def test_program_coverage(self):
        with tempfile.TemporaryDirectory(suffix='-coverage_test') as tempdir:
            coverage_dir = Path(__file__).absolute().parent
            program_src = coverage_dir / 'tests' / 'program'
            subprocess.run(shell_join(['cmake', '-S', program_src, '-B',
                                       tempdir]), shell=True, check=True)
            subprocess.run(shell_join(['cmake', '--build', tempdir]),
                           shell=True, check=True)
            suffix = '.exe' if platform.system() == 'Windows' else ''
            binary = Path(tempdir) / ('test_program' + suffix)

            info_file = Path(tempdir) / 'lcov.info'

            def get_coverage(args=[]):
                subprocess.run([
                    sys.executable,
                    coverage_dir / 'coverage.py',
                    '-o', info_file,
                    '-b', binary,
                    '--', binary] + args, check=True)

                with open(info_file, 'r', encoding='utf-8-sig') as f:
                    return [line.rstrip() for line in f.readlines()]

            # Execute with no arguments.
            lines_no_args = get_coverage()
            # Execute with single argument.
            lines_args = get_coverage(['testarg'])

            # Number of coverage blocks is always the same.
            self.assertEqual(len(lines_no_args), len(lines_args))

            def cut_main_source(lines):
                source_start = lines.index(f'SF:{program_src / "main.cpp"}')
                source_end = lines.index('end_of_record', source_start + 1)
                return lines[source_start:source_end]

            lines_no_args = cut_main_source(lines_no_args)
            lines_args = cut_main_source(lines_args)

            # Line 3 belongs to foo(), line 8 belongs to bar().

            # Only bar() executed with no arguments.
            self.assertTrue('DA:3,0' in lines_no_args)
            self.assertTrue('DA:8,1' in lines_no_args)

            # Only foo() executed if has arguments.
            self.assertTrue('DA:3,1' in lines_args)
            self.assertTrue('DA:8,0' in lines_args)


if __name__ == '__main__':
    unittest.main()
