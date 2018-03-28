#!/usr/bin/env python2

# Check that single sign-on to usb hardware signing token still holds.
# This is done by attempting to sign copied version of signtool.exe itself.

import os
import sys
import time
import subprocess
import shutil


PASSWORD_ENTERED_EXIT_CODE = 20
SIGNED_FILE = 'signed.exe'
SIGNATURE_MARK = 'Issued by: GlobalSign'


signtool_path = subprocess.check_output(['where', 'signtool.exe'], shell=True).rstrip()
print 'Copying %r -> %r' % (signtool_path, SIGNED_FILE)
shutil.copyfile(signtool_path, SIGNED_FILE)
print

print 'Signing using signtool.exe:'
sys.stdout.flush()
subprocess.check_call(['signtool.exe', 'sign', '/a', SIGNED_FILE], shell=True)

print 'Checking signature:'
p = subprocess.Popen(['signtool.exe', 'verify', '/v', SIGNED_FILE], stdout=subprocess.PIPE, shell=True)
stdout, stderr = p.communicate()

if stderr:
    print 'signtool verify returned stderr:'
    print stderr
    sys.exit(10)

if SIGNATURE_MARK in stdout:
    print 'Signature is in place; all OK'
else:
    print 'Signature is missing; signing is FAILED.'
    sys.exit(10)
