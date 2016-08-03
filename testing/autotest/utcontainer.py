# -*- coding: utf-8 -*-
""" Common declarations for autotest/utdocker and autotest/utvb
"""
__author__ = 'Danil Lavrentyuk'

#from subprocess import check_call, call as subcall

__all__ = ['ContainerError', 'UtContainerBase']

class ContainerError(RuntimeError):
    pass

class UtContainerBase(object):
    mode = 'prod' # other possible: 'debug'
    _debug_prefix = "DEBUG(utcontainer): "
    notmp = False  # True -- pass notmp to runut.sh

    @classmethod
    def _debug(cls, text, *args):
        if cls.mode == 'debug':
            if args:
                text = text % args
            print cls._debug_prefix + text

    @classmethod
    def init(cls, buildVars):
        raise NotImplementedError()

    @classmethod
    def done(cls):
        raise NotImplementedError()

    @classmethod
    def _cmdPrefix(cls):
        raise NotImplementedError()

    @classmethod
    def makeCmd(cls, *cmd):
        return cls._cmdPrefix() + (cmd[0] if cmd and type(cmd[0]) == list else list(cmd))

    @classmethod
    def getWrapper(cls):
        return ''

#    @classmethod
#    def containerId(cls):
#        return cls.container['Id']
