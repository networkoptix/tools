
DEFAULT_RUN_LIST_PAGE_SIZE = 20


BYTE_FORMATS = ['', 'K', 'M', 'G', 'T']

def format_bytes(count):
    index = 0
    while (count > 1000) and (index < len(BYTE_FORMATS) - 1):
        count = float(count) / 1024
        index += 1
    return '%.2f%sB' % (count, BYTE_FORMATS[index])
