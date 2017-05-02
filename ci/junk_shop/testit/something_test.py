import os.path
import sys
import logging
import subprocess
import pytest


log = logging.getLogger(__name__)


def run_subprocess(when):
    dir = os.path.abspath(os.path.dirname(__file__))
    subprocess.call([os.path.join(dir, 'test.sh'), when])


@pytest.fixture(scope='session')
def some_session_fixture_1():
    print 'some session fixture 1 stdout'
    print >> sys.stderr, 'some session fixture 1 stderr'
    log.debug('some session fixture 1 log')
    run_subprocess('some session fixture 1 setup')
    return 'session fixture 1 value'

@pytest.fixture(scope='session')
def some_session_fixture_2():
    print 'some session fixture 2 stdout'
    print >> sys.stderr, 'some session fixture 2 stderr'
    log.debug('some session fixture 2 log')
    run_subprocess('some session fixture 2 setup')
    yield 'session fixture 2 value'
    print
    print 'some session fixture teardown 2 stdout'
    print >> sys.stderr, 'some session fixture teardown 2 stderr'
    log.debug('some session fixture teardown 2 log')
    run_subprocess('some session fixture 2 teardown')

@pytest.fixture
def some_fixture_1():
    print
    print 'some fixture 1 stdout'
    print >> sys.stderr, 'some fixture 1 stderr'
    log.debug('some fixture 1 log')
    run_subprocess('some fixture 1 setup')

@pytest.fixture
def some_fixture_2(some_fixture_1, some_session_fixture_1, some_session_fixture_2):
    print 'some fixture 2 stdout'
    print >> sys.stderr, 'some fixture 2 stderr'
    log.debug('some fixture 2 log')
    run_subprocess('some fixture 2 setup')
    yield
    print 'some fixture 2 teardown stdout'
    print >> sys.stderr, 'some fixture 2 teardown stderr'
    log.debug('some fixture teardown 2 log')
    run_subprocess('some fixture 2 teardown')

@pytest.fixture
def some_failing_fixture(some_session_fixture_2):
    print
    print 'some failing fixture stdout'
    print >> sys.stderr, 'some failing fixture stderr'
    log.debug('some failing fixture log')
    assert False, 'This fixture got out of luck'

@pytest.fixture
def some_failing_on_teardown_fixture(some_session_fixture_2):
    print
    print 'some failing on teardown fixture stdout'
    print >> sys.stderr, 'some failing on teardown fixture stderr'
    log.debug('some failing on teardown fixture log')
    yield
    print
    print 'some failing on teardown fixture teardown stdout'
    print >> sys.stderr, 'some failing on teardown fixture teardown stderr'
    log.debug('some failing on teardown fixture teardown log')
    assert False, 'This fixture got out of teardown luck'


def test_some_1(some_fixture_2):
    print
    print 'some test 1 stdout'
    print >> sys.stderr, 'some test 1 stderr'
    log.debug('some test 1 log')
    run_subprocess('test some 1')

def test_some_2(some_fixture_2, some_session_fixture_2):
    local_value = 'some local value'
    print 'some test 2 stdout'
    print >> sys.stderr, 'some test 2 stderr'
    log.debug('some test 2 log')
    run_subprocess('test some 2')
    assert False, 'Bad test, fu!'

def test_some_3(some_failing_fixture):
    print 'some test 3 stdout'
    print >> sys.stderr, 'some test 3 stderr'
    log.debug('some test 3 log')
    assert False, 'Must never reached!'

def test_some_4(some_failing_on_teardown_fixture):
    print 'some test 4 stdout'
    print >> sys.stderr, 'some test 4 stderr'
    log.debug('some test 4 log')
    run_subprocess('test some 4')

def test_some_5(some_fixture_2, some_session_fixture_2, some_failing_on_teardown_fixture):
    print 'some test 5 stdout'
    print >> sys.stderr, 'some test 5 stderr'
    log.debug('some test 5 log')
    run_subprocess('test some 5')
    assert False, 'If you think this test 5 is bad, wait for the fixture...'


def init_logging():
    #format = '%(asctime)-15s %(threadName)-15s %(levelname)-7s %(message)s'
    format = '%(asctime)-15s %(levelname)-7s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format=format)

def main():
    print 'something_test.py global stdout'
    print >> sys.stderr, 'something_test.py global stderr'
    log.debug('something_test.py global log')
    run_subprocess('something_test.py')
    
#init_logging()
main()
#assert False, 'Module is not loadable, sorry man'
