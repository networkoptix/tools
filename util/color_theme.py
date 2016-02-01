#!/bin/python3

import argparse
import re
import os
import shutil
from subprocess import call

def shift_color(color, shift):
    color += shift
    if color < 0:
        color = 0
    if color > 255:
        color = 255
    return color

def warn():
    print('Color should be in full hex HTML color format #xxxxxx.')

def to_rgb(color):
    if color[0] != '#':
        warn()
        return ()

    color = color[1:]
    if len(color) != 6:
        warn()
        return

    r, g, b = color[0:2], color[2:4], color[4:6]
    r, g, b = [int (i, 16) for i in (r, g, b)]
    return r, g, b

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--prefix',   type=str, help='Color name prefix.', default='color')
    parser.add_argument('-c', '--count',    type=int, help='Count of colors to generate.', default=1)
    parser.add_argument('-f', '--first',    type=int, help='First color index.', default=1)
    parser.add_argument('-b', '--base',     type=str, help='Base color', default='#888888')
    parser.add_argument('--rs',             type=int, help='Red sshift', default=8)
    parser.add_argument('--gs',             type=int, help='Green shift', default=8)
    parser.add_argument('--bs',             type=int, help='Blue shift', default=8)
    parser.add_argument('--as',             type=int, help='Alpha shift', default=0)

    args = parser.parse_args()

    red, green, blue = to_rgb(args.base)

    rs = args.rs
    gs = args.gs
    bs = args.bs

    for i in range(0, args.count):
        color = '#%02x%02x%02x' % (red, green, blue)
        color_name = args.prefix + str(i + args.first)
        print('{:<12}"{}",'.format('"{}":'.format(color_name), color))

        red = shift_color(red, rs)
        green = shift_color(green, gs)
        blue = shift_color(blue, bs)

if __name__ == "__main__":
    main()
