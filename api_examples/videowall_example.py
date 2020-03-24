#!/bin/python
# -*- coding: utf-8 -*-

import sys
import requests
import json

host = 'http://localhost:7001'
username = 'admin'
password = 'password'

videowall = json.loads('''
{
  "autorun": true,
  "id": "{B74D1A98-CDAE-495A-BA66-DEFEEE590101}",
  "items": [
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d201}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr1",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 0,
      "snapLeft": 0,
      "snapRight": 0,
      "snapTop": 0
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d202}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr2",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 256,
      "snapLeft": 256,
      "snapRight": 256,
      "snapTop": 256
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d203}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr3",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 512,
      "snapLeft": 512,
      "snapRight": 512,
      "snapTop": 512
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d204}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr4",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 768,
      "snapLeft": 768,
      "snapRight": 768,
      "snapTop": 768
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d205}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr5",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 1024,
      "snapLeft": 1024,
      "snapRight": 1024,
      "snapTop": 1024
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d206}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr6",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 1280,
      "snapLeft": 1280,
      "snapRight": 1280,
      "snapTop": 1280
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d207}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr7",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 1536,
      "snapLeft": 1536,
      "snapRight": 1536,
      "snapTop": 1536
    },
    {
      "guid": "{a9f73993-6e3a-fe06-ccc5-fe323d70d208}",
      "layoutGuid": "{00000000-0000-0000-0000-000000000000}",
      "name": "bbScr8",
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "snapBottom": 1792,
      "snapLeft": 1792,
      "snapRight": 1792,
      "snapTop": 1792
    }
  ],
  "matrices": null,
  "name": "bb_video_wall_4x2_1080",
  "parentId": "{00000000-0000-0000-0000-000000000000}",
  "screens": [
    {
      "desktopHeight": 1080,
      "desktopLeft": 0,
      "desktopTop": 0,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 0
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 1920,
      "desktopTop": 0,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 1
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 3840,
      "desktopTop": 0,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 2
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 5760,
      "desktopTop": 0,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 3
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 0,
      "desktopTop": 1080,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 4
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 1920,
      "desktopTop": 1080,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 5
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 3840,
      "desktopTop": 1080,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 6
    },
    {
      "desktopHeight": 1080,
      "desktopLeft": 5760,
      "desktopTop": 1080,
      "desktopWidth": 1920,
      "layoutHeight": 0,
      "layoutLeft": 0,
      "layoutTop": 0,
      "layoutWidth": 0,
      "pcGuid": "{B74D1A98-CDAE-495A-BA66-DEFEEE591778}",
      "pcIndex": 7
    }
  ],
  "typeId": "{a9f73993-6e3a-fe06-ccc5-fe323d70d67d}",
  "url": ""
}
''')


def check_status(request, verbose):
    if request.status_code == requests.codes.ok:
        if verbose:
            print("Request successfull\n{0}".format(request.text))
        return True
    print("Request error {0}\n{1}".format(request.status_code, request.text))
    return False


def create_videowall():
    print videowall
    r = requests.post(host + '/ec2/saveVideowall', auth=(username, password), json=videowall)
    return check_status(r, True)


def main():
    return create_videowall()


if __name__ == "__main__":
    result = main()
    sys.exit(result)
