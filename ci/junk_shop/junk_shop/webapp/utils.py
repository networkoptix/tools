from collections import namedtuple
from flask import abort


DEFAULT_RUN_LIST_PAGE_SIZE = 20
PAGINATOR_PAGE_LIMIT = 11  # how many pages show in paginator, max

VERSION_AS_INTS_SQL = "string_to_array(run.version, '.')::int[]"

BYTE_FORMATS = ['', 'K', 'M', 'G', 'T']

TESTED_PLATFORMS = ['linux-x64', 'windows-x64', 'mac']

DEFAULT_BUILD_LIST_PAGE_SIZE = 10


StageDescriptor = namedtuple(
    'StageDescriptor', ['name', 'short_name'])


STAGES = [
    StageDescriptor('build', 'build'),
    StageDescriptor('unit', 'ut'),
    StageDescriptor('functional', 'ft'),
    StageDescriptor('cameratest', 'rct'),
    ]

STAGE_NAMES = map(lambda stage: stage.name, STAGES)


def format_bytes(count):
    index = 0
    while (count > 1000) and (index < len(BYTE_FORMATS) - 1):
        count = float(count) / 1024
        index += 1
    return '%.2f%sB' % (count, BYTE_FORMATS[index])


Paginator = namedtuple(
    'Paginator',
    [
        'current_page',
        'pages_range',
        'at_begin',
        'at_end',
        'backward_page',
        'forward_page',
        'first_page',
        'last_page'
    ]
)


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


class PageValueError(Exception):
    pass


def paginator_from_list(current_value, lst):
    '''Create paginator from `lst` of page values,
    current page sets by the `current_value`'''

    if not lst:
        return None

    lst_len = len(lst)

    def get_page(index):
        if index < 0:
            return 0
        if index >= lst_len:
            return lst_len - 1
        return index

    try:
        current_page = lst.index(current_value)
    except ValueError:
        raise PageValueError("Page value '%s' not found" % current_value)

    start = get_page(current_page - PAGINATOR_PAGE_LIMIT / 2 - 1)
    end = get_page(current_page + PAGINATOR_PAGE_LIMIT / 2)
    backward_page = get_page(current_page - PAGINATOR_PAGE_LIMIT + 1)
    forward_page = get_page(current_page + PAGINATOR_PAGE_LIMIT - 1)

    if end - start < PAGINATOR_PAGE_LIMIT:
        end = min(lst_len-1, get_page(start + PAGINATOR_PAGE_LIMIT))
    if end - start < PAGINATOR_PAGE_LIMIT:
        start = max(0, get_page(end - PAGINATOR_PAGE_LIMIT))

    return Paginator(
        current_page=current_value,
        pages_range=lst[start:end+1],
        at_begin=(start == 0),
        at_end=(end == lst_len - 1),
        backward_page=lst[backward_page],
        forward_page=lst[forward_page],
        first_page=lst[0],
        last_page=lst[lst_len-1])


def get_or_abort(Model, id):
    instance = Model.get(id=id)
    if not instance:
        abort(404)
    return instance
