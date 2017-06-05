import socket

def get_lock(lock_name):
    # Without holding a reference to our socket somewhere it gets garbage
    # collected when the function exit
    global lock_socket
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0' + lock_name)
    except socket.error:
        return False
    return True
