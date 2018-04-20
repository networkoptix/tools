import yaml
import re


BUILD_INFO_PATH = 'dist/build_info.yaml'


customization = args['customization']
platform = args['platform']

print 'Parsing %s for customization %r' % (BUILD_INFO_PATH, customization)

build_info = yaml.load(open(BUILD_INFO_PATH))

build_num = build_info['build_num']

server_deb_path = ''
appserver2_ut_path = ''
for file_info in build_info['file_list']:
    if not file_info['platform'] == platform:
        continue
    if not file_info['customization'] == customization:
        continue
    if file_info['type'] == 'distributive' and re.match(r'.+server-.+\.deb', file_info['path']):
        server_deb_path = file_info['path']
    if file_info['type'] == 'unit_tests':
        appserver2_ut_path = file_info['path']

with open('build_info.envfile', 'w') as f:
    print >>f, 'BUILD_NUM=%s' % build_num
    print >>f, 'SERVER_DEB_PATH=%s' % server_deb_path
    print >>f, 'APPSERVER2_UT_PATH=%s' % appserver2_ut_path
with open('build_info.envfile') as f:
    print f.read()
