#!/usr/bin/env python

import yaml
import re

build_info = yaml.load(open('dist/build_info.yaml'))

assert len(build_info['customization_list']) == 1, repr(build_info['customization_list'])
customization = build_info['customization_list'][0]

build_num = build_info['build_num']

server_deb_path = None
appserver2_ut_path = None
for file_info in build_info['file_list']:
    if not file_info['platform'] == '{platform}':
        continue
    if file_info['type'] == 'distributive' and re.match(r'.+server-.+\.deb', file_info['path']):
        server_deb_path = file_info['path']
    if file_info['type'] == 'unit_tests':
        appserver2_ut_path = file_info['path']
assert server_deb_path, 'server deb is missing in build_info.yaml'
assert appserver2_ut_path, 'appserver2_ut is missing in build_info.yaml'

with open('scalability.envfile', 'w') as f:
    print >>f, 'branch={branch}'
    print >>f, 'platform={platform}'
    print >>f, 'customization=%s' % customization
    print >>f, 'build_num=%s' % build_num
    print >>f, 'server_deb_path=%s' % server_deb_path
    print >>f, 'appserver2_ut_path=%s' % appserver2_ut_path
