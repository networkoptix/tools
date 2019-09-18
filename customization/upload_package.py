from urllib.parse import urlencode
import argparse
import requests


DEFAULT_INSTANCE = "https://cloud-test.hdw.mx"


class PackUploader:
    def __init__(self, config):
        self.session = requests.Session()
        self.instance = config.instance
        self.login(config.login, config.password)

    def get_asset_id(self, asset_type, name, customization):
        query = urlencode({"customization": customization, "name": name, "type": asset_type})
        url = f"{self.instance}/admin/cms/get_asset_ids/"
        res = self.session.get(url, params=query)
        res.raise_for_status()
        asset_ids = res.json()[0]
        return asset_ids

    def login(self, login, password):
        res = self.session.post(f"{self.instance}/api/account/login", json={"email": login, "password": password})
        res.raise_for_status()
        self.session.headers['X-CSRFToken'] = self.session.cookies['csrftoken']

    def upload(self, asset_id, package):
        data = {"action": "update_content"}
        files = {'file': (package, open(package, 'rb'), 'application/zip')}
        res = self.session.post(f"{self.instance}/admin/cms/asset_settings/{asset_id}/",
                                files=files, json=data, cookies=self.session.cookies)
        res.raise_for_status()
        print(f"Status Code {res.status_code}")


def get_args():
    description = f"This script will upload a package to the cloud.\nHow to use:" \
                  f"python upload_package.py noptix@networkoptix.com password123 -c default default.zip" \
                  f"\t\t Uploads the default vms package to {DEFAULT_INSTANCE}."
    parser = argparse.ArgumentParser("upload_package", description=description,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("login", help="User's login")
    parser.add_argument("password", help="User's Password")
    parser.add_argument("-i", "--instance", nargs="?", default=DEFAULT_INSTANCE,
                        help=f"The url of the instance that you want to upload a package to.\n"
                        f"Default is {DEFAULT_INSTANCE}")

    parser.add_argument("-n", "--asset_type_name", nargs="?", default="",
                        help="The name of the AssetType you are trying to upload")

    parser.add_argument("-pt", "--asset_type", nargs="?", default="vms",
                        help="The type of the AssetType you are trying to upload")

    parser.add_argument("-c", "--customization",
                        help="The name of the specific customization you want to upload.")

    parser.add_argument("package_path", help="The Absolute path to the package")
    return parser.parse_args()


def main():
    args = get_args()
    uploader = PackUploader(args)
    asset_id = uploader.get_asset_id(args.asset_type, args.asset_type_name, args.customization)
    uploader.upload(asset_id, args.package_path)


if __name__ == "__main__":
    main()
