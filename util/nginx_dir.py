#!/usr/bin/python
#
# Fast NGinx file viewer. `
# ```
#     location ~ ^/files/prefix.*/$ {
#       # sudo apt-get install nginx-extras
#       default_type 'text/html';
#       content_by_lua_block {
#           local p = io.popen(
#               "/usr/bin/python3 /data/develop/tools/util/nginx_dir.py " ..
#               "/var/www/html/test_dir /files/prefix " .. ngx.var.uri .. " advanced 2>&1")
#           ngx.print(p:read("*a"))
#           p:close()
#       }
#     }
# ```
#

import math
import os
import re
import stat
import sys
from datetime import datetime

SIMPLE_COLUMNS = 4


def join_paths(*args):
    return '/'.join([a.strip('/') for a in args])


def size_units(size):
    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    index = 0
    size = float(size)
    while size > 100 and index < len(suffixes):
        size /= 1024.0
        index += 1
    return '%s %s' % (size, suffixes[index])


def numeric_key(text):
    return [0] + [
        int(part) if part.isdigit() else part
        for part in re.split(r'([0-9]+)', text)]


def print_files(path_base, link_base, uri, mode='advanced'):
    path = join_paths(path_base, uri[len(link_base):])
    names = sorted(list(os.listdir(path)), key=numeric_key, reverse=True)

    print('<html><body>')
    print('<h1>%s</h1><hr>' % link_base)
    print('<table style="font-family: monospace; border-spacing: 10px 0;">')

    if mode == 'advanced':
        print('<tr style="font-weight: bold;"><td>Name</td><td>Modified</td><td>Size</td><td>Type</td></tr>')
        for name in names:
            stats = os.stat(join_paths(path, name))
            suffix = '/' if stat.S_ISDIR(stats.st_mode) else ''
            link = '<a href="%s/%s%s">%s</a>%s' % (link_base, name, suffix, name, suffix)
            time = datetime.fromtimestamp(stats.st_mtime).replace(microsecond=0)
            size = size_units(stats.st_blksize * stats.st_blocks)
            node_type = 'Directory' if stat.S_ISDIR(stats.st_mode) else 'File'
            print('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                link, time, '-' if stat.S_ISDIR(stats.st_mode) else size, node_type))
    else:
        print('<tr>')
        links = ['<a href="%s/%s">%s</a><br>' % (link_base, name, name) for name in names]
        part = math.ceil(len(links) / SIMPLE_COLUMNS)
        for i in range(SIMPLE_COLUMNS):
            print('<td width="%s%%">\n%s\n</td>' % (
                math.floor(100 / SIMPLE_COLUMNS), '\n'.join(links[part * i: part * (i + 1)])))
        print('</tr>')

    print('</table>')
    print('<hr><div style="color: gray;">muskov@networkoptix.com</div>')
    print('</body></html>')


if __name__ == '__main__':
    print_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '')
