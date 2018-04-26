#!/usr/bin/env python3

import copy
from typing import Any, List

import pytest

import utils

TEST_DICT = {1: 'one', 2: 'two', 3: 'three'}


def _dict_get(name):
    return TEST_DICT[name]


@pytest.mark.parametrize("request, effect", [
    ('s1.v1=abc', "['s1']['v1'] = 'abc'"),
    ('s2.s3.v2=3', "['s2']['s3']['v2'] = 3"),
    ('v3=[1,2,3]', "['v3'] = [1, 2, 3]"),
])
def test_update_dict(request, effect):
    expected = {
        's1': {'v1': 'hello'},
        's2': {'vx': 1, 's3': {'v1': 1.1, 'v2': 1.2}},
        'v3': {'ve': 'world'},
    }
    actual = copy.deepcopy(expected)
    utils.update_dict(actual, request)
    eval('expected' + effect)
    assert exected == actual


@pytest.mark.parametrize("original, expected_result, options", [
    ([[1, 2, 3, 4, 5], [6, 7, 8]], [1, 6, 2, 7, 3, 8, 4, 5], {}),
    ([[1, 2, 3, 4, 5], [6, 7, 8]], [1, 6, 2, 7, 3, 8, 4, 5], dict(limit=100)),
    ([[1, 2, 3], [11, 12], [21, 22, 23, 24]], [1, 11, 21, 2, 12, 22, 3, 23, 24], {}),
    ([[1, 2, 3], [11, 12], [21, 22, 23, 24]], [1, 11, 21, 2, 12], dict(limit=5)),
])
def test_update_dict(original, expected_result, options):
    assert expected_result == utils.mixed_merge(copy.deepcopy(original), **options)


def test_concurrent():
    expected = {"'one'", "'two'", "'three'", repr(KeyError(4))}
    actual = {repr(r) for r in utils.run_concurrent(_dict_get, [1, 2, 3, 4], thread_count=2)}
    assert expected == actual


@pytest.mark.parametrize("bytes, string, representation", [
    (123, '123', "Size('123')"),
    (1024, '1K', "Size('1K')"),
    (2560, '2.5K', "Size('2.5K')"),
    (3407872, '3.25M', "Size('3.25M')"),
    (23622320128, '22G', "Size('22G')"),
    (1099511627776, '1T', "Size('1T')"),
    (1125899906842624, '1024T', "Size('1024T')"),
])
def test_size(bytes: int, string: str, representation: str):
    size = utils.Size(bytes)
    assert string == str(size)
    assert representation == repr(size)
    size_from_string = utils.Size(string)
    assert size == size_from_string
    assert size_from_string.bytes == bytes


@pytest.mark.parametrize("less, more", [
    (123, '1K'), ('2.5k', 2561), (1099511627776, '1.25T'), ('1T', '2000G')
])
def test_size_compare(less: Any, more: Any):
    less_size, more_size = utils.Size(less), utils.Size(more)
    assert less_size < more_size
    assert less_size != more_size
    assert more_size > less_size


@pytest.mark.parametrize("string", [
    ('123f', 'number', 1.2, '1.2'),
])
def test_size_error(string: int):
    with pytest.raises(TypeError):
        print(utils.Size(string))


@pytest.mark.parametrize("spec, data", [
    ('string', 'hello world'),
    ('bytes', b'hello world'),
    ('json', dict(name='Jack', age=66.6, numbers=[11, 22, 33], alive=True)),
    ('yaml', dict(name='Jill', age=77.7, numbers=[12, 23, 34], alive=False)),
])
def test_file_rw(spec: str, data: Any):
    with utils.TemporaryDirectory() as directory:
        test_file = directory.file('test.file')
        read, write = getattr(test_file, 'read_' + spec), getattr(test_file, 'write_' + spec)

        assert data == read(data)
        with pytest.raises(FileNotFoundError):
            print(read())

        write(data)
        assert data == read()


@pytest.mark.parametrize("extension", ['json', 'yaml'])
@pytest.mark.parametrize("data", [
    ['just', 'a', 'list', 'of', 1, 'items'],
    dict(just='a', simple='dict'),
    dict(more=['complex', 2, 'data', True], structure=3.4),
])
def test_file_parse(extension: str, data: List[str]):
    with utils.TemporaryDirectory() as directory:
        f = directory.file('file.' + extension)
        with pytest.raises(FileNotFoundError):
            print(f.parse())

        getattr(f, 'write_' + extension)(data)
        assert data == f.parse()

