#!/bin/python
# -*- coding: utf-8 -*-

import requests
from timeit import default_timer as timer
from deepdiff import DeepDiff
import urllib3

SERVER_URL = 'https://localhost:7001'
SELF_CHECK_PATH = SERVER_URL + '/rest/experimental/cameras?count=0'
PERF_PATH = SERVER_URL = '/rest/experimental/cameras?count=10000&perf=true'
USER = 'user'
PASSWORD = 'password'
COUNT = 100
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def check_status(request):
    if request.status_code == requests.codes.ok:
        return True
    print("Request error {0}\n{1}".format(request.status_code, request.text))
    return False


def load_reflect(path):
    r = requests.get(path, auth=(USER, PASSWORD), verify=False)
    return r.json() if check_status(r) else None


def load_fusion_json(path):
    r = requests.get(path + '&fusion=true', auth=(USER, PASSWORD), verify=False)
    return r.json() if check_status(r) else None


def load_fusion_ubjson(path):
    r = requests.get(path + '&fusion=true&ubjson=true', auth=(USER, PASSWORD), verify=False)
    check_status(r)


def self_check():
    r1 = load_reflect(SELF_CHECK_PATH)
    r2 = load_fusion_json(SELF_CHECK_PATH)
    ddiff = DeepDiff(r1, r2, ignore_order=True)
    print(ddiff)
    return len(ddiff) == 0


def measure_time(func, count):
    start_time = timer()
    for i in range(COUNT):
        func(PERF_PATH)
    end_time = timer()
    total_time = end_time - start_time
    print(f'Function {func.__name__} Took {total_time:.4f} seconds')


def main():
    if not self_check():
        return

    measure_time(load_reflect, COUNT)
    measure_time(load_fusion_json, COUNT)
    measure_time(load_fusion_ubjson, COUNT)


if __name__ == "__main__":
    main()
