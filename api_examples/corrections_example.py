#!/bin/python
# -*- coding: utf-8 -*-

import sys
import argparse
import requests
import uuid

host = 'http://localhost:7001'
username = 'admin'
password = 'password'


def check_status(request, verbose):
    if request.status_code == requests.codes.ok:
        if verbose:
            print("Request successfull\n{0}".format(request.text))
        return True
    print("Request error {0}\n{1}".format(request.status_code, request.text))
    return False


def tile_id_to_pos(layout, tile_id):
    w = max(layout['fixedWidth'], 1)
    h = layout['fixedHeight']
    left = int(w / 2) * -1
    top = int(h / 2) * -1

    x = tile_id % w
    y = int(tile_id / w)
    return (x + left, y + top)


def request_layout(id, verbose):
    r = requests.get(host + '/ec2/getLayouts?id={}'.format(id), auth=(username, password))
    return r.json() if check_status(r, verbose) else None


def get_layout(id, verbose):
    if verbose:
        print("Looking for layout {}".format(id))
    layouts = request_layout(id, verbose)
    return layouts[0] if layouts else None


def add_camera_to_layout(layout, camera_id, tile_id, verbose):
    tile_pos = tile_id_to_pos(layout, tile_id)
    for item in layout['items']:
        item_pos = (item['left'], item['top'])
        if item_pos == tile_pos:
            if verbose:
                print("Updating existing item")
            item['resourceId'] = ''  # Existing id must be cleaned
            item['resourcePath'] = str(camera_id)
            item['id'] = str(uuid.uuid4())
            return layout

    if verbose:
        print("Adding new item")
    layout['items'].append(
        {
            'id': str(uuid.uuid4()),
            'left': tile_pos[0],
            'top': tile_pos[1],
            'right': tile_pos[0] + 1,
            'bottom': tile_pos[1] + 1,
            'flags': 1,
            'resourcePath': str(camera_id)
        }
    )
    return layout


def save_layout(layout, verbose):
    if verbose:
        print("Saving layout...")
    r = requests.post(host + '/ec2/saveLayout', auth=(username, password), json=layout)
    return check_status(r, verbose)


def set_camera_to_tile(camera_id, screen_id, tile_id, verbose):
    layout = get_layout(screen_id, verbose)
    if not layout:
        print("Layout {} not found".format(screen_id))
        return 2

    layout = add_camera_to_layout(layout, camera_id, tile_id, verbose)
    save_layout(layout, verbose)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--camera', help="Camera id", required=True, type=int)
    parser.add_argument('-s', '--screen', help="Screen logical id", required=True, type=int)
    parser.add_argument('-t', '--tile', help="Tile id", required=True, type=int)
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    args = parser.parse_args()

    return set_camera_to_tile(
        camera_id=args.camera,
        screen_id=args.screen,
        tile_id=args.tile,
        verbose=args.verbose)


if __name__ == "__main__":
    result = main()
    sys.exit(result)
