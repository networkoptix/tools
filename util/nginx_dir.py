#!/usr/bin/python
#
# Plugging as NGinx file viewer:
# ```
#     location ~ ^/files/$ {
#       default_type 'text/html';
#       content_by_lua_block {
#           local p = io.popen("/usr/bin/python /path/to/this-script.py /path/to/files")
#           ngx.print(p:read("*a"))
#           p:close()
#       }
#     }
# ```
#

import os, sys

def print_files(path, link_base, sort=False):
    print("<html><body>")
    print("<h1>%s</h1>" % link_base)
    for f in sorted(list(os.listdir(path))):
        print('<a href="%s/%s">%s</a><br/>' % (link_base, f, f))
    print("</body></html>")

if __name__ == '__main__':
    print_files(sys.argv[1], sys.argv[2])
