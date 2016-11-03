#!/usr/bin/env python
__author__ = 'Danil Lavrentyuk'
import shutil
import time

src = "sample.0.mkv"
dest = "sample.1.mkv"

MARK = 'START_TIMED'
POS = 537 # Note: this position could depend
BLOCK = 100


def main():
    shutil.copyfile(src, dest)

    # check
    with open(src, "rb") as f:
        f.seek(POS)
        data = f.read(BLOCK)
        if data.startswith(MARK):
            print "OK"
        else:
            print "FAIL! Key word '%s' not found at position %s" % (MARK, POS)
            return

    with open(dest, "r+b") as f:
        f.seek(POS+len(MARK)+2)
        timems = str(int(time.time() * 1000))
        print "writting %s" % timems
        f.write(timems)
        f.close()


if __name__ == '__main__':
    main()
