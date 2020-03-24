#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import shutil

def view(size):
    if size < 1024:
        return "{0}".format(size)
    
    size = int(size / 1024)
    if size < 1024:
        return "{0}Kb".format(size)
        
    size = int(size / 1024)
    if size < 1024:
        return "{0}Mb".format(size)        


def main():
    results = dict()
    dir = os.getcwd()
    for dirname, dirnames, filenames in os.walk(dir):
        for filename in filenames:           
            entry = os.path.join(dirname, filename)
            sourceName = entry[:-2]
            extension = os.path.splitext(sourceName)[1][1:]
            size = os.path.getsize(entry)
            if not extension in results:
                results[extension] = 0
            results[extension] += size
            
    tuples = []
    for key, value in results.items():
        tuples.append((value, key))
        
    tuples.sort(reverse = True)
    for t in tuples:
        print "{0}\t\t{1}".format(view(t[0]), t[1])

if __name__ == "__main__":
    main()