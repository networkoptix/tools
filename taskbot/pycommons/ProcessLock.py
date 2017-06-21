import socket
import errno


def get_lock(lock_name):
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exit
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + lock_name)
    except socket.error as x:
        if x.errno == errno.EADDRINUSE:
            return False
        else:
            raise
    return True
