'''Test is_list and is_dict validators

usage:
$ cd $HOME/proj/devtools/ci/projects/test/ && PYTHONPATH=$HOME/proj/devtools/ci/projects ~/venv/bin/pytest validator_test.py -v
'''

import pytest
from pyvalid import accepts, ArgumentValidationError

from utils import dict_inst, is_dict_inst, list_inst, is_list_inst


valid_dict = dict(a=1, b=2)
invalid_dict_1 = dict(a=1, b='c')
invalid_dict_2 = {'a': 1, 2: 'c'}
invalid_dict_3 = [('a', 1), ('b', 2)]

def test_is_dict_inst():
    assert is_dict_inst(valid_dict, str, int)
    assert not is_dict_inst(invalid_dict_1, str, int)
    assert not is_dict_inst(invalid_dict_2, str, int)
    assert not is_dict_inst(invalid_dict_2, str, int)

def test_dict_inst():

    @accepts(value=dict_inst(str, int))
    def dict_fn(value):
        pass

    dict_fn(valid_dict)  # should not raise ArgumentValidationError
    with pytest.raises(ArgumentValidationError):
        dict_fn(invalid_dict_1)
    with pytest.raises(ArgumentValidationError):
        dict_fn(invalid_dict_2)
    with pytest.raises(ArgumentValidationError):
        dict_fn(invalid_dict_3)
    # dict_fn(invalid_dict_3)  # just check error message


valid_list = [1, 2]
invalid_list_1 = [1, '2']
invalid_list_2 = [1, [2]]
invalid_list_3 = {1: 2}

def test_is_list_inst():
    assert is_list_inst(valid_list, int)
    assert not is_list_inst(invalid_list_1, int)
    assert not is_list_inst(invalid_list_2, int)
    assert not is_list_inst(invalid_list_2, int)

def test_list_inst():

    @accepts(value=list_inst(int))
    def list_fn(value):
        pass

    list_fn(valid_list)  # should not raise ArgumentValidationError
    with pytest.raises(ArgumentValidationError):
        list_fn(invalid_list_1)
    with pytest.raises(ArgumentValidationError):
        list_fn(invalid_list_2)
    with pytest.raises(ArgumentValidationError):
        list_fn(invalid_list_3)



valid_dict_list = dict(a=[1, 2], b=[])
invalid_dict_list_1 = dict(a=1, b=[])
invalid_dict_list_2 = {'a': [1], 2: []}
invalid_dict_list_3 = [('a', [1, 2]), ('b', [])]
invalid_dict_list_4 = dict(a=[1, '2'], b=[])

def test_composite_is_dict_list_inst():
    assert is_dict_inst(valid_dict_list, str, list_inst(int))
    assert not is_dict_inst(invalid_dict_list_1, str, list_inst(int))
    assert not is_dict_inst(invalid_dict_list_2, str, list_inst(int))
    assert not is_dict_inst(invalid_dict_list_3, str, list_inst(int))
    assert not is_dict_inst(invalid_dict_list_4, str, list_inst(int))

def test_composite_dict_list_inst():

    @accepts(value=dict_inst(str, list_inst(int)))
    def dict_list_fn(value):
        pass

    dict_list_fn(valid_dict_list)  # should not raise ArgumentValidationError
    with pytest.raises(ArgumentValidationError):
        dict_list_fn(invalid_dict_list_1)
    with pytest.raises(ArgumentValidationError):
        dict_list_fn(invalid_dict_list_2)
    with pytest.raises(ArgumentValidationError):
        dict_list_fn(invalid_dict_list_3)
    with pytest.raises(ArgumentValidationError):
        dict_list_fn(invalid_dict_list_4)
    # dict_list_fn(invalid_dict_list_4)  # just check error message


valid_list_dict = [dict(a=1), dict()]
invalid_list_dict_1 = dict(a=1, b=[])
invalid_list_dict_2 = [dict(a='b')]
invalid_list_dict_3 = [{1: 2}]
invalid_list_dict_4 = [1]

def test_composite_is_list_dict_inst():
    assert is_list_inst(valid_list_dict, dict_inst(str, int))
    assert not is_list_inst(invalid_list_dict_1, dict_inst(str, int))
    assert not is_list_inst(invalid_list_dict_2, dict_inst(str, int))
    assert not is_list_inst(invalid_list_dict_3, dict_inst(str, int))
    assert not is_list_inst(invalid_list_dict_4, dict_inst(str, int))

def test_composite_list_dict_inst():

    @accepts(value=list_inst(dict_inst(str, int)))
    def list_dict_fn(value):
        pass

    list_dict_fn(valid_list_dict)  # should not raise ArgumentValidationError
    with pytest.raises(ArgumentValidationError):
        list_dict_fn(invalid_list_dict_1)
    with pytest.raises(ArgumentValidationError):
        list_dict_fn(invalid_list_dict_2)
    with pytest.raises(ArgumentValidationError):
        list_dict_fn(invalid_list_dict_3)
    with pytest.raises(ArgumentValidationError):
        list_dict_fn(invalid_list_dict_4)
    # list_dict_fn(invalid_list_dict_4)  # just check error message
