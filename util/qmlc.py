import os
import subprocess


def qmlcachegen(extension):
    compiled_extension = extension + 'c'
    for root, dirs, files in os.walk('.'):
        qmls = set(f[:-len(extension)] for f in files if f.endswith(extension))
        qmlcs = set(f[:-len(compiled_extension)] for f in files if f.endswith(compiled_extension))
        qmls -= qmlcs
        files = [root + '\\' + f + extension for f in qmls]
        for f in files:
            print(f)
            subprocess.run(['qmlcachegen', f])


qmlcachegen('.qml')
qmlcachegen('.js')
