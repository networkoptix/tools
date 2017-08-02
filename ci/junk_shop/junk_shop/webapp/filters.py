from datetime import datetime, timedelta
import re
from jinja2 import Markup
from ..utils import datetime_utc_now
from junk_shop.webapp import app


@app.template_filter('to_ident')
def to_indent(value):
    assert value, repr(value)
    assert isinstance(value, (str, unicode)), repr(value)
    result, repl_count = re.subn(r'\s+', '_', value)
    return result

@app.template_filter('format_datetime')
def format_datetime(dt, precise=True):
    if not dt: return dt
    assert isinstance(dt, datetime), repr(dt)
    s = dt.strftime('%Y %b %d')
    if not precise and dt.day < datetime_utc_now().day:
        return Markup(s)
    s += ' <b>' + dt.strftime('%H:%M') + '</b>'
    if precise:
        s += ':' + dt.strftime('%S') + '.%03d' % (dt.microsecond/1000)
    return Markup(s)


@app.template_filter('format_timedelta')
def format_timedelta(d):
    hours, rem = divmod(d.total_seconds(), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, seconds)
    if minutes:
        return '%d:%02d' % (minutes, seconds)
    return '%d.%03d' % (seconds, d.microseconds/1000)

