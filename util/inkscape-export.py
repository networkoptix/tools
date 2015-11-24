#!/bin/python3

import argparse
import re
import os
import shutil
from subprocess import call

base_dpi = 90

def dpi_arg(mdpi, res):
    if res == 'ldpi':
        dpi = mdpi * 0.75
    elif res == 'mdpi':
        dpi = mdpi
    elif res == 'hdpi':
        dpi = mdpi * 1.5
    elif res == 'xhdpi':
        dpi = mdpi * 2
    elif res == 'xxhdpi':
        dpi = mdpi * 3
    elif res == 'xxxhdpi':
        dpi = mdpi * 4
    return ['-d', str(dpi)]

def size_arg(mdpi_size, res):
    if res == 'ldpi':
        size = mdpi_size * 0.75
    elif res == 'mdpi':
        size = mdpi_size
    elif res == 'hdpi':
        size = mdpi_size * 1.5
    elif res == 'xhdpi':
        size = mdpi_size * 2
    elif res == 'xxhdpi':
        size = mdpi_size * 3
    elif res == 'xxxhdpi':
        size = mdpi_size * 4
    return ['-h', str(size)]

def id_arg(sid, dpi):
   return ['-i', sid, '-d', str(dpi)]


parser = argparse.ArgumentParser()
parser.add_argument('fileName', type=str, help='Inkscape SVG file.')
parser.add_argument('-o', '--output-dir', help='Output dir where the resulting icons will be placed.')
parser.add_argument('-b', '--single-base', type=int, help='Base dpi (for mdpi) if svg does not have dpi marks.')
parser.add_argument('-s', '--size', type=int, help='Base size (height) (for mdpi) if svg does not have dpi marks.')
parser.add_argument('-p', '--prefix', type=str, help='Resolution dir prefix.', default='+')

args = parser.parse_args()

output_dir = args.output_dir
if output_dir:
    if not os.path.exists(output_dir):
        print("Directory does not exist: {0}".format(output_dir))
        exit(1)
    if not os.path.isdir(output_dir):
        print("{0} is not a directory".format(output_dir))
        exit(1)
else:
    output_dir = os.getcwd()

mdpi = args.single_base
mdpi_size = args.size

svg = open(args.fileName, 'r')
file_data = svg.read()
svg.close()

exportName = os.path.splitext(os.path.basename(args.fileName))[0] + '.png'

resolutions = ['ldpi', 'mdpi', 'hdpi', 'xhdpi', 'xxhdpi', 'xxxhdpi']
mandatory = ['ldpi', 'mdpi']

found_resolutions = []

if mdpi == 0 and mdpi_size == 0:
    for res in resolutions:
        if file_data.find('id="{0}"'.format(res)) == -1:
            if res in mandatory:
                print("Could not find bound for {0}.".format(res))
                exit(1)
        else:
            found_resolutions.append(res)

for res in resolutions:
    path = os.path.join(output_dir, args.prefix + res)
    if not os.path.exists(path):
        os.mkdir(path)
    name = os.path.join(path, exportName)
    print('Exporting {0} image to {1}.'.format(res, name))

    arg = []

    if mdpi:
        arg = dpi_arg(mdpi, res)
    elif mdpi_size:
        arg = size_arg(mdpi_size, res)
    else:
        if res not in found_resolutions:
            if res == 'hdpi':
                if 'ldpi' in found_resolutions:
                    arg = id_arg('ldpi', base_dpi * 2)
                else:
                    arg = id_arg('mdpi', base_dpi * 1.5)
            elif res == 'xhdpi':
                arg = id_arg('mdpi', base_dpi * 2)
            elif res == 'xxhdpi':
                if 'hdpi' in found_resolutions:
                    arg = id_arg('hdpi', base_dpi * 2)
                else:
                    arg = id_arg('mdpi', base_dpi * 3)
            elif res == 'xxxhdpi':
                if 'xhdpi' in found_resolutions:
                    arg = id_arg('xhdpi', base_dpi * 2)
                else:
                    arg = id_arg('mdpi', base_dpi * 4)

    call_args = ['inkscape', args.fileName, '-e', name] + arg
    call(call_args)
    if res == 'mdpi':
        shutil.copyfile(name, os.path.join(output_dir, exportName))

print('Export finished!')
