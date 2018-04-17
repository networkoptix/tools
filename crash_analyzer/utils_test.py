#!/usr/bin/env python3

from typing import Any, List

import pytest

import utils

TEST_DICT = {1: 'one', 2: 'two', 3: 'three'}


def _dict_get(name):
    return TEST_DICT[name]


def test_concurrent():
    expected = {"'one'", "'two'", "'three'", repr(KeyError(4))}
    actual = {repr(r) for r in utils.run_concurrent(_dict_get, [1, 2, 3, 4], thread_count=2)}
    assert expected == actual


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

