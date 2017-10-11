from collections import namedtuple


DEFAULT_RUN_LIST_PAGE_SIZE = 20
PAGINATOR_PAGE_LIMIT = 11  # how many pages show in paginator, max

VERSION_AS_INTS_SQL = "string_to_array(run.version, '.')::int[]"

BYTE_FORMATS = ['', 'K', 'M', 'G', 'T']


def format_bytes(count):
    index = 0
    while (count > 1000) and (index < len(BYTE_FORMATS) - 1):
        count = float(count) / 1024
        index += 1
    return '%.2f%sB' % (count, BYTE_FORMATS[index])


Paginator = namedtuple('Paginator', 'current_page pages_range at_begin at_end backward_page forward_page first_page last_page')

def paginator(current_page, rec_count, page_size):
    page_count = (rec_count - 1) / page_size + 1
    start = max(0, current_page - PAGINATOR_PAGE_LIMIT/2 - 1)
    end = min(page_count, current_page + PAGINATOR_PAGE_LIMIT/2)
    if end - start < PAGINATOR_PAGE_LIMIT:
        end = min(page_count, start + PAGINATOR_PAGE_LIMIT)
    if end - start < PAGINATOR_PAGE_LIMIT:
        start = max(0, end - PAGINATOR_PAGE_LIMIT)
    return Paginator(
        current_page=current_page,
        pages_range=range(start + 1, end + 1),
        at_begin=(start == 0),
        at_end=(end == page_count),
        backward_page=max(1, current_page - PAGINATOR_PAGE_LIMIT + 1),
        forward_page=min(page_count, current_page + PAGINATOR_PAGE_LIMIT - 1),
        first_page=1,
        last_page=page_count,
        )
