# -*- coding: utf-8 -*-
""" Support unittest execution in a virtual box, controlled by vagrant.
    Interface is compatible with autotest/utdocker.
"""
__author__ = 'Danil Lavrentyuk'

import fnmatch, glob, os, os.path, shutil, sys
from traceback import format_exc
from subprocess import check_call, check_output #, call as subcall, CalledProcessError


if __name__ == '__main__':
    from utcontainer import *
    from tools import clear_dir
    sys.path.append('.') #  just for debug runs
    import testconf as conf
else:
    conf = sys.modules['__main__'].conf
    from .utcontainer import *
    from .tools import clear_dir


def _copyLibs(libpath, dest):
    for mask in ('*.so', '*.so.*'):
        for fn in glob.iglob(os.path.join(libpath, mask)):
            shutil.copy(fn, dest)


def _get_vm_uptime():
    try:
        out = check_output(['./vssh.sh',  conf.UT_BOX_IP, 'cat', '/proc/uptime'])
        return float(out.split()[0])
    except Exception:
        print "WARNING: failed to check VM uptime: " + format_exc()
        return 0

class UtVirtualBox(UtContainerBase):
    """Uses (Virtual Box + vagrant) instead of Docker container.
    Redefines all methods, implementing the same interface.
    """
    _debug_prefix = "DEBUG(utvb): "
    _subdir = ''

    @classmethod
    def init(cls, buildVars):
        # The main idea is: virtual box is always on
        # vargant up does nothing if the box already up
        check_call(conf.VAGR_RUN + [conf.UT_BOX_NAME], shell=False, cwd=conf.UT_VAG_DIR)
        if cls._subdir == '':
            cls._subdir = os.path.join(conf.UT_VAG_DIR, conf.UT_VAG_UT_SUBDIR)
        if not os.path.isdir(cls._subdir):
            os.makedirs(cls._subdir)
        _copyLibs(buildVars.lib_path, cls._subdir)
        _copyLibs(buildVars.qt_lib, cls._subdir)
        for fn in glob.iglob(os.path.join(buildVars.bin_path, "*_ut")):
            shutil.copy(fn, cls._subdir)
        shutil.copy(conf.UT_WRAPPER, cls._subdir)
        # remember, that UT_WRAPPER also clears the temporary directory at the vm

    @classmethod
    def done(cls):
        # 1. Clear _ut and libs
        clear_dir(cls._subdir)
        # 2. ONCE A WEEK RESTART VM
        if _get_vm_uptime() > conf.UT_BOX_TTL:
            #FIXME: move this part into init(), but it will need to check is the VM is created now!
            try:
                check_call(conf.VAGR_DESTROY + [conf.UT_BOX_NAME], shell=False, cwd=conf.UT_VAG_DIR)
            except Exception:
                print "WARNING: failed to destroy VM: " + format_exc()


    @classmethod
    def _cmdPrefix(cls):
        return ['./vssh.sh',  conf.UT_BOX_IP, 'sudo']

    @classmethod
    def getWrapper(cls):
        return os.path.join('/vagrant', conf.UT_VAG_UT_SUBDIR, conf.UT_WRAPPER)



if __name__ == '__main__':
    import subprocess
    from autotest.tools import Build
    if conf.PROJECT_ROOT.startswith('~'):
        conf.PROJECT_ROOT = os.path.expanduser(conf.PROJECT_ROOT)
    conf.BUILD_CONF_PATH = os.path.join(conf.PROJECT_ROOT, conf.BUILD_CONF_SUBPATH)
    Build.load_vars(conf)
    UtVirtualBox.mode = "debug"
    UtVirtualBox.init(Build)
    cmd = ['ls', '-l']
    subprocess.call(UtVirtualBox.makeCmd(UtVirtualBox.getWrapper(), 'common_ut'))
    print "Finishing..."
    UtVirtualBox.done()
