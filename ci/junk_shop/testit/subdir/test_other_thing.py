import pytest

@pytest.fixture
def some_fixture():
    print 'some fixture in other test'
    return 'some other fixture value'

def test_1(some_fixture):
    print 'test 1 from other thing'

def test_2(some_fixture):
    print 'test 2 from other thing'
