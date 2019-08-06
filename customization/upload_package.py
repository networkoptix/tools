from urllib.parse import urlencode
import argparse
import requests


DEFAULT_INSTANCE = "https://cloud-test.hdw.mx"


class PackUploader:
    def __init__(self, config):
        self.session = requests.Session()
        self.instance = config.instance
        self.login(config.login, config.password)

    def get_product_id(self, product_type, name, customization):
        query = urlencode({"customization": customization, "name": name, "type": product_type})
        url = f"{self.instance}/admin/cms/get_product_ids/"
        res = self.session.get(url, params=query)
        res.raise_for_status()
        product_ids = res.json()[0]
        return product_ids

    def login(self, login, password):
        res = self.session.post(f"{self.instance}/api/account/login", json={"email": login, "password": password})
        res.raise_for_status()
        self.session.headers['X-CSRFToken'] = self.session.cookies['csrftoken']

    def upload(self, product_id, package):
        data = {"action": "update_content"}
        files = {'file': (package, open(package, 'rb'), 'application/zip')}
        res = self.session.post(f"{self.instance}/admin/cms/product_settings/{product_id}/",
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

    parser.add_argument("-n", "--product_type_name", nargs="?", default="",
                        help="The name of the ProductType you are trying to upload")

    parser.add_argument("-pt", "--product_type", nargs="?", default="vms",
                        help="The type of the ProductType you are trying to upload")

    parser.add_argument("-c", "--customization",
                        help="The name of the specific customization you want to upload.")

    parser.add_argument("package_path", help="The Absolute path to the package")
    return parser.parse_args()


def main():
    args = get_args()
    uploader = PackUploader(args)
    product_id = uploader.get_product_id(args.product_type, args.product_type_name, args.customization)
    uploader.upload(product_id, args.package_path)


if __name__ == "__main__":
    main()
