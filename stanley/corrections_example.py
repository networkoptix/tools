#!/bin/python2
# -*- coding: utf-8 -*-

import sys
import argparse
import requests
import uuid
import pyfscache

host = 'http://localhost:7001'
username = 'admin'
password = 'password'

cache = pyfscache.FSCache('.', minutes=10)


def check_status(request, verbose):
    if request.status_code == requests.codes.ok:
        return True
    if verbose:
        print("Request error {0}\n{1}".format(request.status_code, request.text))
    return False


def tile_id_to_pos(tile_id):
    if tile_id == 1:
        return (1, 0)
    if tile_id == 2:
        return (0, 1)
    if tile_id == 3:
        return (1, 1)
    return (0, 0)


@cache
def get_videowall(verbose):
    if verbose:
        print("Requesting videowalls list")
    r = requests.get(host + '/ec2/getVideowalls', auth=(username, password))
    if not check_status(r, verbose):
        return None
    videowalls = r.json()
    if len(videowalls) != 1:
        return None
    return videowalls[0]


def get_layout(id, verbose):
    r = requests.get(host + '/ec2/getLayouts?id={}'.format(id), auth=(username, password))
    if not check_status(r, verbose):
        return None
    layouts = r.json()
    if len(layouts) != 1:
        return None
    return layouts[0]


@cache
def get_all_cameras(verbose):
    r = requests.get(host + '/ec2/getCamerasEx', auth=(username, password))
    if not check_status(r, verbose):
        return None
    return r.json()


def get_camera(id, verbose):
    if verbose:
        print("Looking for camera {}".format(id))
    string_id = str(id)
    cameras = get_all_cameras(verbose)
    if not cameras:
        return None

    for camera in cameras:
        if camera['logicalId'] == string_id:
            return camera
    return None


def add_camera_to_layout(layout, camera_uuid, tile_id, verbose):
    tile_pos = tile_id_to_pos(tile_id)
    for item in layout['items']:
        item_pos = (item['left'], item['top'])
        if item_pos == tile_pos:
            if verbose:
                print("Updating existing item")
            item['resourceId'] = camera_uuid
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
            'resourceId': camera_uuid
        }
    )
    return layout


def save_layout(layout, verbose):
    if verbose:
        print("Saving layout...")
    r = requests.post(host + '/ec2/saveLayout', auth=(username, password), json=layout)
    return check_status(r, verbose)


def set_camera_to_tile(camera_id, screen_id, tile_id, verbose):
    videowall = get_videowall(verbose)
    if not videowall:
        if verbose:
            print("Videowall not found (or there are too many of them)")
        return 1

    items = sorted(videowall['items'], key=lambda item: item['name'])
    if len(items) <= screen_id:
        if verbose:
            print("Screen {} not found".format(screen_id))
        return 2

    layout_guid = uuid.UUID(items[screen_id]['layoutGuid'])
    if layout_guid.int == 0:
        if verbose:
            print("Layous is not set for the screen {}".format(screen_id))
        return 3

    camera = get_camera(camera_id, verbose)
    if not camera:
        if verbose:
            print("Camera {} not found".format(camera_id))
        return 4
    camera_uuid = camera['id']

    layout = get_layout(layout_guid, verbose)
    if not layout:
        if verbose:
            print("Layout {} not found".format(layout_guid))
        return 5

    layout = add_camera_to_layout(layout, camera_uuid, tile_id, verbose)
    save_layout(layout, verbose)
    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--camera', help="Camera id", required=True, type=int)
    parser.add_argument('-s', '--screen', help="Screen id", required=True, type=int)
    parser.add_argument('-t', '--tile', help="Tile id", required=True, type=int,
                        choices=range(0, 4))
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    args = parser.parse_args()

    return set_camera_to_tile(
        camera_id=args.camera,
        screen_id=args.screen,
        tile_id=args.tile,
        verbose=args.verbose)


if __name__ == "__main__":
    result = main()
    if result != 0:
        print("Error {}".format(result))
    sys.exit(result)
