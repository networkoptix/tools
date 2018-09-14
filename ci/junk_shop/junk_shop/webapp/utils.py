from collections import namedtuple

from flask import abort


DEFAULT_RUN_LIST_PAGE_SIZE = 20
PAGINATOR_PAGE_LIMIT = 11  # how many pages show in paginator, max

VERSION_AS_INTS_SQL = "string_to_array(run.version, '.')::int[]"

BYTE_FORMATS = ['', 'K', 'M', 'G', 'T']

DEFAULT_BUILD_LIST_PAGE_SIZE = 10


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


def paginator_from_list(current_value, lst):

    last_page = len(lst) - 1

    def get_page(index):
        if index < 0:
            return 0
        if index > last_page:
            return last_page
        return index

    def get_page_value(index):
        return lst[index] if index <= last_page else 0

    try:
        current_page = lst.index(current_value)
    except ValueError:
        current_page = 0

    start = get_page(current_page - PAGINATOR_PAGE_LIMIT / 2 - 1)
    end = get_page(current_page + PAGINATOR_PAGE_LIMIT / 2)
    backward_page = get_page(current_page - PAGINATOR_PAGE_LIMIT + 1)
    forward_page = get_page(current_page + PAGINATOR_PAGE_LIMIT - 1)

    if end - start < PAGINATOR_PAGE_LIMIT:
        end = get_page(start + PAGINATOR_PAGE_LIMIT)
    if end - start < PAGINATOR_PAGE_LIMIT:
        start = get_page(end - PAGINATOR_PAGE_LIMIT)

    return Paginator(
        current_page=current_value,
        pages_range=lst[start:end],
        at_begin=(start == 0),
        at_end=(end == last_page),
        backward_page=get_page_value(backward_page),
        forward_page=get_page_value(forward_page),
        first_page=get_page_value(0),
        last_page=get_page_value(last_page))


def get_or_abort(Model, id):
    instance = Model.get(id=id)
    if not instance:
        abort(404)
    return instance
