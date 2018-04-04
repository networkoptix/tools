#!/usr/bin/env python3

import os
import shutil
import logging

import pytest

import utils

TEST_DICT = {1: 'one', 2: 'two', 3: 'three'}


def _dict_get(name):
    return TEST_DICT[name]


def test_concurrent():
    assert {"'one'", "'two'", "'three'", repr(KeyError(4))} == \
        {repr(r) for r in utils.run_concurrent(_dict_get, [1, 2, 3, 4], thread_count=2)}


@pytest.mark.parametrize("spec, data, args", [
    ('data', 'hello world', {}),
    ('data', b'hello world', {'mode': 'b'}),
    ('json', dict(name='Jack', age=66.6, numbers=[11, 22, 33], alive=True), {}),
    ('yaml', dict(name='Jill', age=77.7, numbers=[12, 23, 34], alive=False), {}),
])
def test_file_rw(spec, data, args):
    with utils.TemporaryDirectory() as tmp_directory:
        f = utils.File(tmp_directory, 'test.file')
        r, w = getattr(f, 'read_' + spec), getattr(f, 'write_' + spec)

        assert data == r(data, **args)
        with pytest.raises(FileNotFoundError):
            print(r(**args))

        w(data, **args)
        assert data == r(**args)

@pytest.mark.parametrize("extension, data", [
    ('json', ["just", "a", "list"]),
    ('yaml', ["one", "more", "list"]),
])
def test_file_parse(extension, data):
    with utils.TemporaryDirectory() as tmp_directory:
        f = utils.File('{}/file.{}'.format(tmp_directory, extension))
        with pytest.raises(FileNotFoundError):
            print(f.parse())

        getattr(f, 'write_' + extension)(data)
        assert data == f.parse()


@pytest.mark.parametrize("make, updates", [
    (utils.CacheSet, ({"one", "two", "three"}, {"fore"}, {"five"})),
    (utils.CacheDict, ({"one": "two", "three": "fore"}, {"five": "six"})),
])
def test_cache(make, updates):
    with utils.TemporaryDirectory() as tmp_directory:
        first = make(tmp_directory, 'test.cache')
        assert not first
        for update in updates:
            first.update(update)
            first.save()
            second = make(tmp_directory, 'test.cache')
            assert first == second
