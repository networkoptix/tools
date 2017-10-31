import re
import argparse


# pattern, severity
SEVERITY_PATTERNS = [
    # Linux
    (r':\d+:\d+:\s+(\S+\s+)?error:', 'error'),
    (r':\s+error:', 'error'),
    (r':\s+undefined reference to', 'error'),
    (r'\s+Error\s+\d+', 'error'),
    (r':\d+:\d+:\s+warning:', 'warning'),
    (r':\d+: Warning:', 'warning'),  # [INFO] {standard input}:50870: Warning: end of file not at end of a line; newline inserted
    (r':\d+: Error:', 'error'),      # [INFO] {standard input}:51067: Error: unknown pseudo-op: `.lbe293'
    (r'internal compiler error:', 'error'),  # ..qmetatype.h:736:1: internal compiler error: Segmentation fault
    # Windows
    (r':\s+(fatal\s)?error\s[A-Z]+\d+\s*:', 'error'),
    (r':\s+warning\s[A-Z]+\d+\s*:', 'warning'),
    # Mac
    (r'ERROR:', 'error'),
    # Common
    (r'\[ERROR\]', 'error'),
    (r'FAILURE', 'error'),
    (r'\[WARNING\]', 'warning'),
    (r'SKIPPED', 'warning'),
    (r'SUCCESS', 'success'),
    ]


def match_output_line(line):
    for pattern, severity in SEVERITY_PATTERNS:
        if re.search(pattern, line):
            return severity
    return None


def test_output():
    parser = argparse.ArgumentParser()
    parser.add_argument('severities', help='Which severities to reports, one chars for each: ewsn (n=none)')
    parser.add_argument('file', type=file, help='Build output to parse')
    args = parser.parse_args()
    for line in args.file:
        severity = match_output_line(line)
        ch = severity[0] if severity else 'n'
        if ch in args.severities:
            print (severity or 'none').ljust(7), line.rstrip()

if __name__ == '__main__':
    test_output()
