#!/usr/bin/python

import requests

from dataclasses import dataclass
from pprint import pprint

SOURCE_URL='https://junkshop.lan.hdw.mx/api/get_fails?draw=2&columns%5B0%5D%5Bdata%5D=name&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B1%5D%5Bdata%5D=last_build&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=false&columns%5B1%5D%5Borderable%5D=false&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B2%5D%5Bdata%5D=last_fail&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=false&columns%5B2%5D%5Borderable%5D=true&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B3%5D%5Bdata%5D=first_build&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=false&columns%5B3%5D%5Borderable%5D=false&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B4%5D%5Bdata%5D=first_fail&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=false&columns%5B4%5D%5Borderable%5D=true&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false&columns%5B5%5D%5Bdata%5D=count&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=false&columns%5B5%5D%5Borderable%5D=true&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false&order%5B0%5D%5Bcolumn%5D=5&order%5B0%5D%5Bdir%5D=desc&start=0&length=20&search%5Bvalue%5D=&search%5Bregex%5D=false&csrf_token=ImNmMzYxNThkNTViMmMyZDMwYTFiYzBlYTc5MTAwODVjZTZmYWFiZTMi.YzMbMg.rLSg_uM4WHqhxm9Y9bVSE2kwRPU&project=gitlab&branch=master&platform=linux-x64&test_bundle=unit&date_from=2022+Sep+20&date_to=2022+Sep+27&_=1664293683789'
LABEL_URL='https://junkshop.lan.hdw.mx/fails?project=develop&platform=linux-x64&branch=master'

SOURCE_VARIANTS = [{
    '=master': '=master',
    '=vms_5.1': '=master',
    '=vms_5.0_patch': '=master',
}, {
    "=linux-x64": "=linux-x64",
    "=windows-x64": "=linux-x64",
}]

def enum_urls(source_template=SOURCE_URL, label_template=LABEL_URL, variants=SOURCE_VARIANTS):
    if len(variants) == 0:
        yield (label_template, source_template)
        return
    first_variants, *tail_variants = variants
    for k, v in first_variants.items():
        source = source_template.replace(v, k)
        label = label_template.replace(v, k)
        for childK, childV in enum_urls(source, label, tail_variants):
            yield (childK, childV)


def URL_TEMPLATE():
    template = SOURCE_URL
    for k, v in SOURCE_REPLACE.items():
        template.replace(k, v)
    return template


class TestFails:
    def __init__(self):
        self.tests = {}

    def save_report(self, variant, report):
        def save(label, name, count, **kv):
            test = self.tests.setdefault(name, {})
            test[label] = count
            test['total'] = count + test.get('total', 0)

        for fail in report:
            save(label=variant, **fail)

    def sorted_by(self, sort_field, filter):
        flat = list([dict(name=k, **v) for k, v in self.tests.items()])
        result = list([v for v in flat if not filter or filter(v)])
        return sorted(result, key=lambda v: v[sort_field])

    @staticmethod
    def report_line(name, total, **variants):
        details = ', '.join([f'{k} - {v}' for k, v in variants.items()])
        return f'{name} - {total}: {details}'

def main():
    fails = TestFails()
    for label, url in enum_urls():
        print(f'Fetching: {label}')
        report = requests.get(url).json()['data'];
        print(f'  => loaded {len(report)} failures')
        fails.save_report(label, report)

    for test in fails.sorted_by('name', lambda v: v['total'] > 1):
        print(TestFails.report_line(**test))


if __name__ == '__main__':
    main()
