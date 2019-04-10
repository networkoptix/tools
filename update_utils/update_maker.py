import requests # we request it!
import hashlib # for md5 calculation
import json
import os # for probing FS
from shutil import rmtree

# Creds used to login to jenkins page
jenkins_auth = ('dkargin', '')

unpack_dir = "targetdir"


# Generate URL for downloading all build artifacts in one archive
# We do not use it for real. We download individual packages
def get_build_artifacts_url(build_num):
    return "http://jenkins.enk.me/job/ci/job/vms/%d/artifact/*zip*/archive.zip" % build_num


prefix = "nxwitness"

client_platforms = [
    ('linux64', 'linux', 'x64_ubuntu'), 
    ('win64', 'windows', 'x64_winxp')] # There can be a mac as well

server_platforms = [
    ('linux64', 'linux', 'x64_ubuntu'),
    ('bpi', 'linux', 'arm_bpi'),
    ('win64', 'windows', 'x64_winxp')
]

os_variants = {
    'windows': '7',
    'linux64': '14.04',
}

# From old jenkins
#http://jenkins.enk.me/job/ci/job/vms/1156/artifact/nxwitness-server_update-4.0.0.1156-bpi-beta-test.zip
# From the new jenkins
# http://10.0.0.120/develop/vms/1916/default/all/update/nxwitness-server_update-4.0.0.1916-linux64-beta-test.zip


def make_filename(**kwargs):
    return "{prefix}-{component}_update-{version}.{build}-{platform}{suffix}.zip".format(**kwargs)


def make_base_url(**kwargs):
    return "https://beta.networkoptix.com/beta-builds/{customization}/{build}/".format(**kwargs)


# Makes url to get update source
def make_update_source_url(**kwargs):
    # prefix, component, version, build, platform, suffix
    # baseurl = "http://jenkins.enk.me/job/ci/job/vms/{build}/artifact/".format(**kwargs)
    # http://10.0.0.120/develop/vms/{build}/default/all/update/
    # https://beta.networkoptix.com/beta-builds/default/28608/
    baseurl = "https://beta.networkoptix.com/beta-builds/{customization}/{build}/".format(**kwargs)
    url = make_filename(**kwargs)
    return baseurl + url


def generate_update_folder(build_num, customization="default"):
    # Client packages
    context = dict(
        prefix="nxwitness", 
        version="4.0.0", suffix="-beta-test", build=build_num,
        customization=customization
    )
    # We store output there
    updates_version_dir = "vms_updates/updates/%s/%d"%(customization, build_num)
    print("Preparing output dir: " + updates_version_dir)
    
    # Need to clean target directory
    if os.path.isdir(updates_version_dir):
        rmtree(updates_version_dir)
    try:
        os.makedirs(updates_version_dir)
    except OSError as e:
        pass
    
    # Download helper. Downloads a file to a target directory and calculates its length and md5
    def download_package(context):
        url = make_update_source_url(**context)
        target_file = make_filename(**context)
        print("Downloading {file} from {url}".format(file=target_file, url=url))
        
        with requests.get(url, stream=True, auth=jenkins_auth) as r:
            length = 0
            md5 = hashlib.md5()
            with open(updates_version_dir + "/" + target_file, "wb") as handle:
                for chunk in r.iter_content(chunk_size=1024): 
                    length += len(chunk)
                    md5.update(chunk)
                    handle.write(chunk)
            result = {'file':target_file, 'size':length, 'md5':md5.hexdigest()}
            print("Finished downloading {file}, {size} bytes, md5={md5}".format(**result))
            return result
    
    base_url_path = make_base_url(**context)
    base_package_index = requests.get(base_url_path + "packages.json").json()
    eula_path = base_package_index.get("eulaLink", "")
    eula_data = ""
    if eula_path != "":
        eula_data = requests.get(base_url_path + eula_data).text
    # This dictionary will be dumped to packages.json
    output_package_index = {
        "version":"%s.%d"%(context['version'], build_num),
        "cloudHost": base_package_index.get("cloudHost", "cloud-test.hdw.mx"),
        "eulaVersion": 2,
        "eulaLink": "http://new.eula.com/eulaText",
        "eula": eula_data,
        "packages": [],
    }
    
    # Downloads update files and updates data for index.json
    def get_and_index_packages(component, platforms, dstPackages):
        # Do for clients
        context['component'] = component    
        for pkg_platform, system, arch in platforms:        
            context['platform'] = pkg_platform
            package_v1 = download_package(context)
            if package_v1 is not None:
                package_v2 = {
                    "component": component,
                    "arch": arch,
                    "platform": pkg_platform,
                    "variant": system,
                    "variantVersion": os_variants.get(system, system+"-nover"),
                    "file": package_v1.get('file'),
                    "size": package_v1.get('size'),
                    "md5": package_v1.get('md5')
                }
                output_package_index['packages'].append(package_v2)
                      
    get_and_index_packages('client', client_platforms, 'clientPackages')
    get_and_index_packages('server', server_platforms, 'packages')
            
    # Dump new packages.json
    with open(updates_version_dir + '/packages.json', 'w') as outfile:
        server_packages = output_package_index["packages"]
        
        json.dump(output_package_index, outfile, indent = 4, ensure_ascii = False)


def download_file(base_url_path, filename, output_dir, **kwargs):
    """
    Download helper. Downloads a file to a target directory and calculates its length and md5
    :param base_url_path: base URL to build folder
    :param filename: filename to be downloaded
    :param output_dir: output directory to store this file
    :return:
    """
    url = base_url_path + filename
    print("Downloading {file} from {url} to {dir}".format(file=filename, url=url, dir=output_dir))

    with requests.get(url, stream=True, **kwargs) as r:
        length = 0
        md5 = hashlib.md5()
        output_name = output_dir + "/" + filename if output_dir != "" else filename
        with open(output_name, "wb") as handle:
            for chunk in r.iter_content(chunk_size=1024):
                length += len(chunk)
                md5.update(chunk)
                handle.write(chunk)
        result = dict(file=filename, size=length, md5=md5.hexdigest())
        print("Finished downloading {file}, {size} bytes, md5={md5}".format(**result))
        return result


class Generator:
    def __init__(self, base_url, output_dir="vms_updates/updates", **context):
        # Base_url contains url templates like:
        # "https://beta.networkoptix.com/beta-builds/{customization}/{build}/".format(**kwargs)
        # "http://artifacts.lan.hdw.mx/release/vms_4.0/{build}/{customization}/all/"
        self.base_url = base_url
        self.output_dir = output_dir
        self.base_context = context

    def prepare_output_dir(self, customization, build):
        """
        Prepares output directory
        :param customization: customization name
        :param build:int build number
        :return:str generated path for update contents
        """
        path = "{base}/{customization}/{build}".format(base=self.output_dir, customization=customization, build=build)
        # Need to clean target directory
        if os.path.isdir(path):
            rmtree(path)
        try:
            os.makedirs(path)
        except OSError as e:
            pass
        return path

    def set_out_dir(self, dir):
        """Set output directory"""
        self.output_dir = dir

    def get_build_folder(self, customization, build, **kwargs):
        """
        Get a path to the folder with specified build
        :param kwargs:
        :return:str URL to build folder
        """
        # "https://beta.networkoptix.com/beta-builds/{customization}/{build}/".format(**kwargs)
        # "http://artifacts.lan.hdw.mx/release/vms_4.0/{build}/{customization}/all/update/"
        return self.base_url.format(customization=customization, build=build, **kwargs)

    def generate_build_folder(self, build_num, customization="default"):
        # Copies all packages from source URL to target path
        # Client packages
        context = dict(
            prefix="nxwitness",
            version="4.0.0", suffix="-beta-test", build=build_num,
            customization=customization
        )

        # We store output there
        updates_version_dir = self.prepare_output_dir(customization, build_num)

        base_url_path = self.get_build_folder(customization, build_num)

        # We can fail here. Beta-builds contains packages.json, but jenkins output does not contain any
        base_package_index = requests.get(base_url_path + "packages.json").json()
        eula_path = base_package_index.get("eulaLink", "")
        eula_data = ""
        if eula_path != "":
            eula_data = requests.get(base_url_path + eula_path).text

        # This dictionary will be dumped to packages.json
        """
        output_package_index = {
            "version":"%s.%d"%(context['version'], build_num),
            "cloudHost": base_package_index.get("cloudHost", "cloud-test.hdw.mx"),
            "eulaVersion": 2,
            "eulaLink": "http://new.eula.com/eulaText",
            "eula": eula_data,
            "packages": [],
        }
        """

        if "eula" not in base_package_index:
            base_package_index["eula"] = eula_data

        packages = base_package_index.get("packages", [])
        good_packages = []
        for package in packages:
            file = package["file"]
            try:
                download_file(base_url_path, file, updates_version_dir)
                good_packages.append(package)
            except:
                print("Failed to obtain file %s" % file)

        base_package_index["packages"] = good_packages

        # Dump new packages.json
        with open(updates_version_dir + '/packages.json', 'w') as outfile:
            server_packages = base_package_index["packages"]
            json.dump(base_package_index, outfile, indent=4, ensure_ascii=False)


def makeBetaBuildsGenerator(output_dir="vms_updates/updates"):
    return Generator("https://beta.networkoptix.com/beta-builds/{customization}/{build}/", output_dir)


def makeJenkinsArtifactsGenerator(output_dir="vms_updates/updates"):
    return Generator("http://artifacts.lan.hdw.mx/release/vms_4.0/{build}/{customization}/all/update/", output_dir)
