# This file provides utilites to fill in update server with data from our jenkins

import requests # we request it!
import hashlib # for md5 calculation
import json
import os # for probing FS
from shutil import rmtree

prefix = "nxwitness"

"""
Example output:

Preparing output dir: /var/www/vms_updates/updates/default/2155
Downloading nxwitness-client_update-4.0.0.2155-linux64-beta-test.zip
Downloading nxwitness-client_update-4.0.0.2155-win64-beta-test.zip
Downloading nxwitness-server_update-4.0.0.2155-linux64-beta-test.zip
Downloading nxwitness-server_update-4.0.0.2155-bpi-beta-test.zip
Downloading nxwitness-server_update-4.0.0.2155-win64-beta-test.zip
"""

# pkg_platform, system, arch, variant, version
client_platforms = [
    ('linux64', 'linux', 'x64', 'ubuntu', '14.04'), 
    ('win64', 'windows', 'x64', 'winxp', '7.0')] # There can be a mac as well

server_platforms = [
    ('linux64', 'linux', 'x64', 'ubuntu', '14.04'),
    ('bpi', 'linux', 'arm', 'bananapi', '7.0'),
    ('win64', 'windows', 'x64', 'winxp', '7.0')
]

# From old jenkins
# http://jenkins.enk.me/job/ci/job/vms/1156/artifact/nxwitness-server_update-4.0.0.1156-bpi-beta-test.zip
# From the new jenkins
# http://10.0.0.120/develop/vms/1916/default/all/update/nxwitness-server_update-4.0.0.1916-linux64-beta-test.zip

def make_filename(**kwargs):
    return "{prefix}-{component}_update-{version}.{build}-{platform}{suffix}.zip".format(**kwargs)

# Makes url to get update source
def make_update_source_url(**kwargs):
    # prefix, component, version, build, platform, suffix
    # baseurl = "http://jenkins.enk.me/job/ci/job/vms/{build}/artifact/".format(**kwargs)
    # http://10.0.0.120/develop/vms/{build}/default/all/update/
    baseurl = "http://10.0.0.120/develop/vms/{build}/default/all/update/".format(**kwargs)
    url = make_filename(**kwargs)
    return baseurl + url

# Download helper. Downloads a file to a target directory and calculates its length and md5
# @param auth - tuple with user and a password. Used for authentication in our jenkins
# @param output_dir - directory to store files
def download(context, auth, output_dir):
    url = make_update_source_url(**context)
    target_file = make_filename(**context)
    print("Downloading "+ target_file)

    with requests.get(url, stream=True, auth=auth) as r:
        length = 0
        md5 = hashlib.md5()
        with open(output_dir + "/" + target_file, "wb") as handle:
            for chunk in r.iter_content(chunk_size=1024): 
                length += len(chunk)
                md5.update(chunk)
                handle.write(chunk)
        result = {'file':target_file, 'size':length, 'md5':md5.hexdigest()}
        print("Finished downloading {file}, {size} bytes, md5={md5}".format(**result))
        return result

# update_root = "vms_updates/updates"
def generate_update_folder(update_root, build_num, jenkins_auth, customization="default"):
    # Client packages
    context = {"prefix":"nxwitness", "version":"4.0.0", "suffix":"-beta-test", "build":build_num}
    # We store output there
    updates_version_dir = "%s/%s/%d"%(update_root, customization, build_num)
    print("Preparing output dir: " + updates_version_dir)
    
    # Need to clean target directory
    if os.path.isdir(updates_version_dir):
        rmtree(updates_version_dir)
    try:
        os.makedirs(updates_version_dir)
    except OSError as e:
        pass
    
    # This dictionary will be dumped to update.json
    output_index = {
        "version":"%s.%d"%(context['version'], build_num),
        "cloudHost":"cloud-test.hdw.mx",
        "eulaVersion": 2,
        "eulaLink": "http://new.eula.com/eulaText",
        "packages": {},
        "clientPackages": {},
    }
    
    # This dictionary will be dumped to packages.json
    output_index_v2 = {
        "version":"%s.%d"%(context['version'], build_num),
        "cloudHost":"cloud-test.hdw.mx",
        "eulaVersion": 2,
        "eulaLink": "http://new.eula.com/eulaText",
        "packages": [],
    }
    
    # Downloads update packages and updates the data for update.json
    def get_and_index_packages(component, platforms, dstPackages):
        # Do for clients
        context['component'] = component
        # Trying to download all the instances, that enumerated in [platforms]
        for pkg_platform, system, arch, variant, version in platforms:        
            context['platform'] = pkg_platform
            package_v1 = download(context, jenkins_auth, updates_version_dir)
            if package_v1 is not None:
                if not (system in output_index[dstPackages]):
                    output_index[dstPackages][system] = {}
                output_index[dstPackages][system][arch] = package_v1
                
                package_v2 = {
                    "component": component,
                    "arch": arch,
                    "platform": system,
                    "variant": variant,
                    "variantVersion": version,
                    "file": package_v1.get('file'),
                    "size": package_v1.get('size'),
                    "md5": package_v1.get('md5')
                }
                output_index_v2['packages'].append(package_v2)
                
                      
    get_and_index_packages('client', client_platforms, 'clientPackages')
    get_and_index_packages('server', server_platforms, 'packages')
    
    # Dump json with target data
    with open(updates_version_dir + '/update.json', 'w') as outfile:
        json.dump(output_index, outfile, indent = 4, ensure_ascii = False)
        
    # Dump new packages.json
    with open(updates_version_dir + '/packages.json', 'w') as outfile:
        server_packages = output_index["packages"]
        
        json.dump(output_index_v2, outfile, indent = 4, ensure_ascii = False)
        
