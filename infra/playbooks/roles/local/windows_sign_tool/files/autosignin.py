#!/usr/bin/env python2

# This script enters password for hardware signing token. It is supposed to be autorun on user autologin.

# Requirements:
# * Install:
#     https://www.globalsign.com/support/adobe/GlobalSign_SAC_9.0-x64.msi
# * Enter into registry:
#     [HKEY_CURRENT_USER\SOFTWARE\SAFENET\AUTHENTICATION\SAC\GENERAL]
#     "SingleLogon"=dword:00000001
# which allows entering password only once per server start, and also allows this script do in automatically.
# See also:
# https://networkoptix.atlassian.net/wiki/spaces/SD/pages/408289282/Signing+windows+executables+with+hardware+key

# KEY_PASSWORD is expected to be in environment


import os
import sys
import time
import subprocess
import shutil
import threading

import pywintypes
import win32con
import win32gui


PASSWORD_DIALOG_CAPTION = 'Token Logon'
PASSWORD_DIALOG_CLASS = '#32770'
PASSWORD_EDIT_ID = 0x3ea

PASSWORD_ENTERED_EXIT_CODE = 20
SIGNED_FILE = 'signed.exe'
SIGNATURE_MARK = 'Issued by: GlobalSign'


def enum_handler(hwnd, (password, entered_count)):
    if (not win32gui.IsWindowVisible(hwnd) or
            win32gui.GetWindowText(hwnd) != PASSWORD_DIALOG_CAPTION or
            win32gui.GetClassName(hwnd) != PASSWORD_DIALOG_CLASS):
        return True
    ed_hwnd = win32gui.GetDlgItem(hwnd, PASSWORD_EDIT_ID)
    win32gui.SendMessage(ed_hwnd, win32con.WM_SETTEXT, None, password)
    win32gui.PostMessage(ed_hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    print('Password is entered to token dialog.')
    entered_count[0] += 1
    return True

def clicker_thread(stop_flag, password, entered_count):
    while not stop_flag[0]:
        try:
            win32gui.EnumWindows(enum_handler, (password, entered_count))
            time.sleep(1)
        except pywintypes.error as x:
            print 'Error enumerating windows:', x.winerror, x
            break
            # raise x



print
print 'Signing in at: %s (UTC+%d)' % (time.asctime(), -time.timezone/3600)
key_password = os.environ['KEY_PASSWORD']  # key is missing if not added from credentials

signtool_path = subprocess.check_output(['where', 'signtool.exe'], shell=True).rstrip()
print 'Copying %r -> %r' % (signtool_path, SIGNED_FILE)
shutil.copyfile(signtool_path, SIGNED_FILE)

stop_flag = [False]
entered_count = [0]
clicker = threading.Thread(target=clicker_thread, args=(stop_flag, key_password, entered_count))
clicker.start()
print 'Clicker thread is started.'

print 'Signing using signtool.exe:'
sys.stdout.flush()
subprocess.check_call(['signtool.exe', 'sign', '/a', SIGNED_FILE], shell=True)

print 'Stopping clicker thread...'
stop_flag[0] = True
clicker.join()
print 'Clicker thread is stopped.'
print 'Password was entered %d times' % entered_count[0]

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

if entered_count[0] > 0:
    # mark jenkins job yellow when password was actually required and entered
    sys.exit(PASSWORD_ENTERED_EXIT_CODE)
