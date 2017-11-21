import os
import subprocess
import sys
import argparse

current_dir = os.path.dirname(os.path.realpath(__file__))
os.system('hg recover')

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--devtools', default="default", help="devtools branch")
parser.add_argument('-v', '--vms', help="vms branch")
parser.add_argument('-c', '--cloud', help="cloud branch")
parser.add_argument('-m', '--mobile', help="mobile branch")
args = parser.parse_args()

devtools_branch = args.devtools
vms_branch = args.vms
cloud_branch = args.cloud
mobile_branch = args.mobile

if not devtools_branch:
    devtools_branch = 'default'
print ("Devtools Branch: %s" % devtools_branch)
if not os.path.exists('../devtools'):
    os.makedirs('../devtools')
os.chdir('../devtools')
os.system('hg pull|| hg clone ssh://hg@hdw.mx/devtools .')
os.system('hg up %s -C' % devtools_branch)
os.chdir(current_dir)
#sys.path.insert(0, '../devtools/translation/')

if args.vms:
    vms_branch = args.vms
    print ("VMS Branch: %s" % vms_branch)
    os.system('hg pull')
    os.system('hg update %s -C' % vms_branch)
    return_code = subprocess.call(['python', '../devtools/translation/update_translations.py', '-l', 'en_US'])
    os.system('hg pul')
    os.system('hg up -m')
    os.system('hg commit -m"Translatable files updated"')
    os.system('hg push')
    os.chdir('translation')
    os.system('vms_up.bat')
    os.chdir(current_dir)
#else:
#    vms_branch = subprocess.check_output(['hg', 'branch']).replace("\n", "")

if args.mobile:
    mobile_branch = args.mobile
    print ("Mobile Branch: %s" % mobile_branch)
    os.system('hg pull')
    os.system('hg update %s -C' % mobile_branch)
    return_code = subprocess.call(['python', '../devtools/translation/update_translations.py', '-l', 'en_US'])
    #print(return_code)
    os.system('hg pul')
    os.system('hg up -m')
    os.system('hg commit -m"Translatable files updated"')
    os.system('hg push')
    os.chdir('translation')
    os.system('mobile_up.bat')
    os.chdir(current_dir)

if args.cloud:
    cloud_branch = args.cloud
    print ("Cloud Branch: %s" % cloud_branch)
    os.system('hg pull')
    os.system('hg update %s -C' % cloud_branch)
    cloud_branch = os.getenv('cloud_branch')
    os.chdir('translation')
    os.system('cloud_up.bat')
    os.chdir(current_dir)