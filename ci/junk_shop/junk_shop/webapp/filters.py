from datetime import datetime, timedelta
import re
from jinja2 import Markup, escape
from ..utils import datetime_utc_now, timedelta_to_str
from junk_shop.webapp import app


JIRA_REF_REGEX = r'(([a-z]+|[A-z]+)\-\d+)'


@app.template_filter('to_ident')
def to_indent(value):
    assert value, repr(value)
    assert isinstance(value, (str, unicode)), repr(value)
    result, repl_count = re.subn(r'[\s.-]+', '_', value)
    return result

@app.template_filter('format_datetime')
def format_datetime(dt, precise=True):
    if not dt: return dt
    assert isinstance(dt, datetime), repr(dt)
    now = datetime_utc_now()
    if now.year == dt.year:
        s = dt.strftime('%b %d')
    else:
        s = dt.strftime('%Y %b %d')
    if not precise and (dt.timetuple()[:2] < now.timetuple()[:2] or dt.day < datetime_utc_now().day - 10):
        return Markup(s)
    if dt.timetuple()[:3] < now.timetuple()[:3]:
        s += ' ' + dt.strftime('%H:%M')
    else:
        s += ' <b>' + dt.strftime('%H:%M') + '</b>'
    if precise:
        s += ':' + dt.strftime('%S') + '.%03d' % (dt.microsecond/1000)
    return Markup(s)


format_timedelta = app.template_filter('format_timedelta')(timedelta_to_str)

def format_timedelta(d):
    hours, rem = divmod(d.total_seconds(), 3600)
    minutes, seconds = divmod(rem, 60)
    if hours:
        return '%d:%02d:%02d' % (hours, minutes, seconds)
    if minutes:
        return '%d:%02d' % (minutes, seconds)
    return '%d.%03d' % (seconds, d.microseconds/1000)

def make_jira_ref(jira_url, ref):
    return '<a class="link" href="%s/%s">%s</a>' % (jira_url, ref.upper(), ref)

# convert JIRA items to http links
@app.template_filter('format_commit_message')
def format_commit_message(message):
    jira_url = app.config.get('JIRA_URL')
    if not jira_url:
        return message
    message = str(escape(message))
    ref_list = [group[0] for group in re.findall(JIRA_REF_REGEX, message)]
    for ref in ref_list:
        message = message.replace(ref, make_jira_ref(jira_url, ref))
    return Markup(message)


@app.template_filter('format_revision')
def format_revision(revision, repository_url):
    format = app.config.get('SCM_BROWSER_URL_FORMAT')
    if not format or not repository_url:
        return ''  # do not show anything then
    repository_name = repository_url.split('/')[-1].lower()
    dashed_repository_name = repository_name.replace('_', '-')
    ref = format.format(repository_name=dashed_repository_name, revision=revision)
    return Markup('<a class="link" href="%s">%s</a>' % (ref, repository_name))

@app.template_filter('decorate_revision')
def decorate_revision(revision, repository_url):
    format = app.config.get('SCM_BROWSER_URL_FORMAT')
    if not format or not repository_url:
        return revision
    repository_name = repository_url.split('/')[-1].lower()
    dashed_repository_name = repository_name.replace('_', '-')
    ref = format.format(repository_name=dashed_repository_name, revision=revision)
    return Markup('<a class="link" href="%s">%s</a>' % (ref, revision))
