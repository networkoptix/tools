from __future__ import print_function
import os
import subprocess
import sys
import argparse

script_dir = os.path.dirname(os.path.realpath(__file__))
current_dir = os.getcwd()
os.system('hg recover')

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--devtools', default="default", help="devtools branch")
parser.add_argument('-v', '--vms', help="vms branch")
parser.add_argument('-c', '--cloud', help="cloud branch")
parser.add_argument('-m', '--mobile', help="mobile branch")
args = parser.parse_args()

## This is to be moved to a Jenkins job
#######################################
#devtools_branch = args.devtools
#if not devtools_branch:
#    devtools_branch = 'default'
#print ("Devtools Branch: %s" % devtools_branch)
#if not os.path.exists('../devtools'):
#    os.makedirs('../devtools')
#os.chdir('../devtools')
#os.system('hg pull|| hg clone ssh://hg@hdw.mx/devtools .')
#os.system('hg up %s -C' % devtools_branch)
#os.chdir(current_dir)
#######################################

if args.vms:
    vms_branch = args.vms
    print ("VMS Branch: %s" % vms_branch)
    os.system('hg pull')
    os.system('hg update %s -C' % vms_branch)
    return_code = subprocess.call([sys.executable, '../devtools/translation/update_translations.py', '-l', 'en_US'])
    #os.system('hg pul')
    #os.system('hg up -m')
    #os.system('hg commit -m"Translatable files updated"')
    #os.system('hg push')
    os.chdir('translation')
    os.system('vms_up.bat')
    os.chdir(current_dir)

if args.mobile:
    mobile_branch = args.mobile
    print ("Mobile Branch: %s" % mobile_branch)
    os.system('hg pull')
    os.system('hg update %s -C' % mobile_branch)
    return_code = subprocess.call([sys.executable, '../devtools/translation/update_translations.py', '-l', 'en_US'])
    #os.system('hg pul')
    #os.system('hg up -m')
    #os.system('hg commit -m"Translatable files updated"')
    #os.system('hg push')
    os.chdir('translation')
    os.system('mobile_up.bat')
    os.chdir(current_dir)

if args.cloud:
    cloud_branch = args.cloud
    print ("Cloud Branch: %s" % cloud_branch)
    os.system('hg pull')
    os.system('hg update %s -C' % cloud_branch)
    os.chdir('translation')
    os.system('cloud_up.bat')
    os.chdir(current_dir)