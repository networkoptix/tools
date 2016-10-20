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
    from logger import debug, log, raw_log
    sys.path.append('.') #  just for debug runs
    import testconf as conf
else:
    conf = sys.modules['__main__'].conf
    from .utcontainer import *
    from .tools import clear_dir
    from .logger import debug, log, raw_log

TOHOST = "%s:" % conf.UT_BOX_IP

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
    _libsCopied = set()
    notmp = True

    @classmethod
    def init(cls, buildVars):
        # The main idea is: virtual box is always on
        # vargant up does nothing if the box already up
        check_call(conf.VAGR_RUN + [conf.UT_BOX_NAME], shell=False, cwd=conf.UT_VAG_DIR)
        #if cls._subdir == '':
        #    cls._subdir = os.path.join(conf.UT_VAG_DIR, conf.UT_VAG_UT_SUBDIR)
        #if not os.path.isdir(cls._subdir):
        #    os.makedirs(cls._subdir)
        log("Copy tests and libs into the box...")
        #debug("buildVars:\n%s", "\n".join(
        #        "\t%s = %s" % (attr, getattr(buildVars, attr)) for attr in
        #        ('lib_path', 'qt_lib', 'bin_path')
        #    ))
        cls._clear_files()
        cls._copyLibs(buildVars.lib_path, cls._subdir)
        cls._copyLibs(buildVars.qt_lib, cls._subdir)
        toCopy = []
        for fn in glob.iglob(os.path.join(buildVars.bin_path, "*_ut")):
            toCopy.append(fn)
            if len(toCopy) > 4:
                #debug("Copy: %s", toCopy)
                cls._copy2box(*toCopy)
                toCopy = []
        if len(toCopy) > 0:
            #debug("Copy: %s", toCopy)
            cls._copy2box(*toCopy)
        cls._copy2box(conf.UT_WRAPPER)
        #check_call(cls._cmdPrefix() + ['ls', '-l'])
        # remember, that UT_WRAPPER also clears the temporary directory at the vm

    @classmethod
    def done(cls):
        # 1. Clear _ut and libs
        cls._clear_files()
        #clear_dir(cls._subdir)
        # 2. ONCE A WEEK RESTART VM
        if _get_vm_uptime() > conf.UT_BOX_TTL:
            #FIXME: move this part into init(), but it will need to check is the VM is created now!
            try:
                check_call(conf.VAGR_DESTROY + [conf.UT_BOX_NAME], shell=False, cwd=conf.UT_VAG_DIR)
            except Exception:
                log("WARNING: failed to destroy VM: " + format_exc())

    @classmethod
    def _clear_files(cls):
        try:
            check_call(cls._cmdPrefix() + ['rm', '-f', '*_ut', '*.so*'])
            cls._libsCopied.clear()
        except Exception:
            pass #

    @classmethod
    def _cmdPrefix(cls):
        return ['./vssh.sh',  conf.UT_BOX_IP, 'sudo']

    @classmethod
    def _copy2box(cls, *files):
        #debug("_copy2box: %s", "\n\t".join(files))
        check_call(['./vscpto.sh', TOHOST] + list(files))


    @classmethod
    def getWrapper(cls):
        #return os.path.join('/vagrant', conf.UT_VAG_UT_SUBDIR, conf.UT_WRAPPER)
        return os.path.join('.', conf.UT_WRAPPER)

    @classmethod
    def _copyLibs(cls, libpath, dest):
        #vm_ut_dir = os.path.join('/vagrant', conf.UT_VAG_UT_SUBDIR)
        toCopy = []
        for mask in ('*.so', '*.so.*'):
            for fn in glob.iglob(os.path.join(libpath, mask)):
                fnBase = os.path.basename(fn)
                if fnBase in cls._libsCopied:
                    #debug("Ignored already copied lib %s", fnBase)
                    continue
                if os.path.islink(fn):
                    #debug("_copyLibs linking %s -> %s", os.path.basename(os.readlink(fn)), fnBase)
                    check_call(cls._cmdPrefix() + ["ln", '-s', '-f',
                        os.path.basename(os.readlink(fn)), fnBase])
                else:
                    toCopy.append(fn)
                    if len(toCopy) > 4:
                        cls._copy2box(*toCopy)
                        toCopy = []
                    #shutil.copyfile(fn, os.path.join(dest, os.path.basename(fn)))
                cls._libsCopied.add(fnBase)
        if len(toCopy) > 0:
            cls._copy2box(*toCopy)


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
