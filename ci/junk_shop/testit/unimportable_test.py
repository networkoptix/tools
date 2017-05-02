import os.path
import sys
import logging
import subprocess


log = logging.getLogger(__name__)

def run_subprocess(when):
    dir = os.path.abspath(os.path.dirname(__file__))
    subprocess.call([os.path.join(dir, 'test.sh'), when])


def test_some_1():
    print 'unimportable test some 1 stdout'

def main():
    print 'unimportable_test.py global stdout'
    print >> sys.stderr, 'unimportable_test.py global stderr'
    log.debug('unimportable_test.py global log')
    run_subprocess('unimportable_test.py')
    # assert False, 'unimportable_test.py module is not loadable, sorry man'

main()
