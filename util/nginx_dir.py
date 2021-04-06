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

import os
import stat
import sys
from datetime import datetime


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


def print_files(path_base, link_base, uri, mode='advanced'):
    print('<html><body>')
    print('<h1>%s</h1>' % link_base)
    if mode == 'advanced':
        print('<table style="font-family: monospace; border-spacing: 10px 0;">')
        print('<tr style="font-weight: bold;"><td>Name</td><td>Modified</td><td>Size</td><td>Type</td></tr>')

    path = join_paths(path_base, uri[len(link_base):])
    for name in sorted(list(os.listdir(path)), reverse=True):
        if mode == 'advanced':
            stats = os.stat(join_paths(path, name))
            suffix = '/' if stat.S_ISDIR(stats.st_mode) else ''
            link = '<a href="%s/%s%s">%s</a>%s' % (link_base, name, suffix, name, suffix)
            time = datetime.fromtimestamp(stats.st_mtime).replace(microsecond=0)
            size = size_units(stats.st_blksize * stats.st_blocks)
            node_type = 'Directory' if stat.S_ISDIR(stats.st_mode) else 'File'
            print('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (
                link, time, '-' if stat.S_ISDIR(stats.st_mode) else size, node_type))
        else:
            print('<a href="%s/%s">%s</a><br>' % (link_base, name, name))

    print('</table>')
    print('</body></html>')


if __name__ == '__main__':
    print_files(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '')
