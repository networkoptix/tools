#!/usr/bin/env python3

import yaml

import crash_info

LEVELS = set(['CRITICAL', 'ERROR', 'WARNING'])


class Record:
    def __init__(self, line: str):
        self.date, self.time, self.level, self.text = (x.strip() for x in line.split(' ', 3))

    def __repr__(self):
        return '<{} {} {}>'.format(type(self).__name__, self.level, self.text)
        
    @property
    def key(self):
        r = self.report
        if not r:
            return self.text
            
        return self.text.replace(r.name, '<{} from {} {} {} {}>'.format(
            type(self).__name__, r.component, r.full_version, r.customization, r.platform))

    @property
    def report(self):
        for part in self.text.replace('"', ' ').replace("'", ' ').split(' '):
            try:
                return crash_info.Report(part)
            except crash_info.ReportNameError:
                pass


class Reader:
    def __init__(self):
        self.records = {level: {} for level in LEVELS}  # type: Dict[str, Dict[str, List[Record]]]
        
    def read_file(self, file_path: str, include: list, exclude: list):
        with open(file_path) as f:
            for line in f:
                if exclude and any(e in line for e in exclude):
                    continue
                if include and any(i not in line for i in include):
                    continue
                try:
                    record = Record(line)
                except ValueError:
                    continue
                if record.level in LEVELS:
                    self.records[record.level].setdefault(record.key, []).append(record)
                
    def report(self, count: int, requested_levels: set):
        def records_by_level(level):
            records_by_key = self.records[level]
            if not records_by_key:
                return 'no records'

            key_counts = []
            for key, records in records_by_key.items():
                key_counts.append(dict(title=key, count=len(records)))
            key_counts.sort(key=lambda k: k['count'], reverse=True)

            result = key_counts[:count]
            rest_count = sum(r['count'] for r in key_counts[count:])
            if rest_count:
                result.append(dict(title='more records', count=rest_count))

            return result

        return {level: records_by_level(level) for level in LEVELS if level in requested_levels}


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('log_files', nargs='+', help='log files to read')
    parser.add_argument('-c', '--count', type=int, default=0, help='Records to show per level')
    parser.add_argument('-l', '--levels', type=str, default=','.join(LEVELS))
    parser.add_argument('-i', '--include', type=str, default='', help='Parse only records with')
    parser.add_argument('-e', '--exclude', type=str, default='', help='Parse only records without')
    
    def get_list(value):
        return [v for v in value.split(',') if v]
        
    arguments = parser.parse_args()
    reader = Reader()
    for path in arguments.log_files:
        reader.read_file(path, get_list(arguments.include), get_list(arguments.exclude))
        
    report = reader.report(arguments.count, arguments.levels.upper().split(','))
    print(yaml.dump(report, default_flow_style=False, width=float("inf")))