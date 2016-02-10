#!/usr/bin/env python2
# -*- coding: UTF-8 -*-
"Interprocess lock through an abstract socket. Linux only"
__author__ = 'Danil Lavrentyuk'
import socket

Locks = dict() # Without this our locks will be garbage collected

def lock(lock_name):
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + lock_name)
    except socket.error:
        return False
    Locks[lock_name] = lock_socket
    return True


def unlock(lock_name, safe=False):
    if safe and lock_name not in Locks:
        return
    Locks[lock_name].close()
    del Locks[lock_name]

def _test():
    print "Testing..."
    name = 'socklock-test'
    if lock(name):
        print "%s - locked. OK" % (name,)
    else:
        print "%s - failed to lock" % (name,)
        return
    if name in Locks:
        print "lock stored. OK"
    unlock(name)
    print "unlocked. OK"


if __name__ == '__main__':
    _test()
