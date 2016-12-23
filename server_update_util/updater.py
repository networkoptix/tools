#!/usr/bin/env python

import os
import argparse
from zipfile import ZipFile
import json
import hashlib
import requests
import urllib
import glob

UPDATE_ID = "__update__"
CHUNK_SIZE = 1024 * 1024

def get_md5(file_name):
    md5 = hashlib.md5()
    with open(file_name, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()

class server_info:
    def __init__(self, guid, sys_info, url, name):
        self.guid = guid
        self.system_info = sys_info
        self.url = url
        self.name = name

class update_info:
    def __init__(self, sys_info, file_name):
        self.system_info = sys_info
        self.file_name = file_name
        self.md5 = get_md5(file_name)

def ping_server(url, guid):
    print("Checking url {}".format(url))
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return False
        result = json.loads(r.text)
        return result["reply"]["moduleGuid"] == guid
    except:
        return False

def pick_server_address(addresses, port, guid):
    for address in addresses:
        if address.find(':') < 0:
            address = address + ':' + str(port)
        if ping_server("http://{}/api/ping".format(address), guid):
            return address
    return None

def get_server_information(url):
    print("Getting server information...")

    r = requests.get(url + "/api/moduleInformationAuthenticated")
    if r.status_code != 200:
        print("Could not get information")
        print(r.status_code, r.reason)
        return None

    module_information = json.loads(r.text)["reply"]
    sys_info = module_information["systemInformation"]
    sys_info = "{} {} {}".format(sys_info["platform"], sys_info["arch"], sys_info["modification"])

    return server_info(
        guid=module_information["id"],
        sys_info=sys_info,
        url=url,
        name=module_information["name"])

def gather_server_information(url, ignore_offline=False, ignored_servers=[]):
    print("Gathering servers information...")

    r = requests.get(url + "/ec2/getMediaServersEx")
    if r.status_code != 200:
        print("Could not gather information")
        print(r.status_code, r.reason)
        return None

    servers_data = json.loads(r.text)

    parsed_url = urllib.parse.urlparse(url)
    user = parsed_url.username
    password = parsed_url.password

    result = []

    for server in servers_data:
        server_id = server["id"]

        if server_id in ignored_servers:
            continue

        port = urllib.parse.urlparse(server["url"]).port
        system_info = server["systemInfo"]

        print("Found server {} {} ({})".format(server["name"], server_id, system_info))

        server_url = None

        address = pick_server_address(
            server["networkAddresses"].split(";"),
            port,
            server_id)
        if not address:
            server_url = url + "/proxy/" + urllib.parse.quote(server_id)
            print("Direct address was not found.")
            print("Trying proxy URL {}".format(server_url))
            if not ping_server(server_url, server_id):
                print("Could not find available address for server.")
                if ignore_offline:
                    print("Ignoring server {}".format(server_id))
                    continue
                else:
                    print("Aborting...")
                    return None
        else:
            server_url = "http://{}:{}@{}".format(user, password, address)
            print("Using direct URL {}".format(server_url))

        result.append(server_info(guid=server_id, sys_info=system_info, url=server_url, name=server["name"]))

    return result

def get_info_for_zip(file_name):
    print("Checking zip file {}".format(file_name))

    with ZipFile(file_name) as zf:
        info = json.loads(zf.read("update.json").decode("utf-8"))
        if info.get("client", False):
            print("This is a client update file. Ignoring...")
            return None
        sys_info = "{} {} {}".format(info["platform"], info["arch"], info["modification"])
        print("OK: ({})".format(sys_info))
        return sys_info

def gather_update_information(path):
    print("Gathering updates information...")

    result = {}

    for file_name in glob.glob(os.path.join(path, "*.zip")):
        info = get_info_for_zip(file_name)
        if info:
            result[info] = update_info(info, file_name)

    return result

def upload_update(server, update):
    offset = 0

    while True:
        try:
            req = server.url + "/api/installUpdate?updateId={}&offset=-1".format(UPDATE_ID)
            r = requests.post(req, data=update.md5)
            if r.status_code != 200:
                print("Cannot start update uploading")
                print(r.status_code, r.reason)
                return False

            offset = int(json.loads(r.text)["reply"]["offset"])
            break

        except(KeyboardInterrupt):
            return False
        except:
            print("Upload initialization has failed. Retrying...")
            continue

    with open(update.file_name, "rb") as uf:
        uf.seek(0, os.SEEK_END)
        file_size = uf.tell()

        while True:
            print("\r{}%".format(int(offset * 100 / file_size)), end='')
            uf.seek(offset)
            data = uf.read(CHUNK_SIZE)

            req = server.url + "/api/installUpdate?updateId={}&offset={}".format(UPDATE_ID, offset)

            try:
                r = requests.post(req, data=data)
                if r.status_code != 200:
                    print()
                    print("Cannot upload chunk {}".format(offset))
                    print(r.status_code, r.reason)
                    return False

                offset = int(json.loads(r.text)["reply"]["offset"])

            except(KeyboardInterrupt):
                return False

            except:
                print()
                print("Chunk upload has failed. Retrying...")
                continue

            if not data:
                break

    print()

    return True

def upload_updates(servers, updates):
    i = 1
    for server in servers:
        update = updates[server.system_info]
        print("Uploading update file {} to server {} {} ({}/{})".format(
            update.file_name, server.name, server.guid, i, len(servers)))
        i += 1
        if not upload_update(server, update):
            return False
    return True

def check_update_coverage(servers, updates):
    for server in servers:
        if not updates.get(server.system_info, None):
            print("Update file for server {} {} ({}) not found".format(
                server.name, server.guid, server.system_info))
            return False
    return True

def install_update(server):
    print("Send install request to server {} {}".format(server.name, server.guid))

    req = server.url + "/api/installUpdate?updateId={}".format(UPDATE_ID)

    r = requests.post(req)
    if r.status_code != 200:
        print("Cannot start update on server {}".format(server.guid))
        print(r.status_code, r.reason)
        return False

    return True

def install_updates(servers):
    print("Installing updates...")
    result = True
    for server in servers:
        result = result and install_update(server)
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("url", type=str, help="Server URL.")
    parser.add_argument("--updates-dir", help="Directory containing update files.", default=os.getcwd())
    parser.add_argument("--install", help="Send install command to servers.", action="store_true")
    parser.add_argument("--one-server", help="Upload update to the specified server only.", action="store_true")
    parser.add_argument("--ignore-offline", help="Ignore offline servers.", action="store_true")
    parser.add_argument("--ignore", help="Ignore the specified servers.", nargs="+", metavar="IDs")

    args = parser.parse_args()

    servers = None
    if args.one_server:
        info = get_server_information(args.url)
        if info:
            servers = [info]
    else:
        servers = gather_server_information(
            args.url,
            ignored_servers=args.ignore,
            ignore_offline=args.ignore_offline)

    if not servers:
        print("No servers were found")
        exit(0)

    print()
    updates = gather_update_information(args.updates_dir)
    print()
    if not check_update_coverage(servers, updates):
        exit(1)
    if not upload_updates(servers, updates):
        exit(1)
    if args.install:
        print()
        if not install_updates(servers):
            exit(1)
