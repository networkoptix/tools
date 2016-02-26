import platform
import sys

supported_platforms = [
    "windows",
    "linux",
    "macos",
    "android",
    "ios"
]

supported_arches = [
    "x64",
    "x86",
    "arm"
]

supported_boxes = [
    "none",
    "rpi",
    "bpi",
    "isd",
    "isd_s2",
    "windows"
]

def detect_platform():
    platform = sys.platform
    if platform.startswith("win32") or platform.startswith("cygwin"):
        return "windows"
    elif platform.startswith("linux"):
        return "linux"
    elif platform.startswith("darwin"):
        return "macos"
    else:
        return "unknown"

def detect_arch():
    arch = platform.machine()
    if arch == "x86_64" or arch == "AMD64":
        return "x64"

    return arch
