from datetime import datetime, timedelta
from collections import namedtuple
import re

from jinja2 import Markup, escape

from .utils import datetime_utc_now, timedelta_to_str


JIRA_REF_REGEX = r'(([a-z]+|[A-z]+)\-\d+)'


class JinjaFilters(object):

    Config = namedtuple('JinjaFilters_Config', 'jira_url scm_browser_url_format')

    def __init__(self, config):
        self._config = config

    def install(self, jinja_env):
        for name in dir(self):
            if name.startswith('_') or name == 'install': continue
            jinja_env.filters[name] = getattr(self, name)

    def to_ident(self, value):
        assert value, repr(value)
        assert isinstance(value, (str, unicode)), repr(value)
        result, repl_count = re.subn(r'[\s.-]+', '_', value)
        return result

    def format_datetime(self, dt, precise=True):
        if not dt: return dt
        assert isinstance(dt, datetime), repr(dt)
        now = datetime_utc_now()
        if now.year == dt.year:
            s = dt.strftime('%b %d')
        else:
            s = dt.strftime('%Y %b %d')
        if dt.timetuple()[:3] < now.timetuple()[:3]:
            s += ' ' + dt.strftime('%H:%M')
        else:
            s += ' <b>' + dt.strftime('%H:%M') + '</b>'
        if precise:
            s += ':' + dt.strftime('%S') + '.%03d' % (dt.microsecond/1000)
        return Markup(s)


    def format_timedelta(self, td):
        return timedelta_to_str(td)

    def _make_jira_ref(self, jira_url, ref):
        return '<a class="link" href="%s/%s">%s</a>' % (jira_url, ref.upper(), ref)

    # convert JIRA items to http links
    def format_commit_message(self, message):
        jira_url = self._config.jira_url
        if not jira_url:
            return message
        message = unicode(escape(message))
        ref_list = [group[0] for group in re.findall(JIRA_REF_REGEX, message)]
        for ref in ref_list:
            message = message.replace(ref, self._make_jira_ref(jira_url, ref))
        return Markup(message)

    def format_revision(self, revision, repository_url):
        format = self._config.scm_browser_url_format
        if not format or not repository_url:
            return ''  # do not show anything then
        repository_name = repository_url.split('/')[-1].lower()
        dashed_repository_name = repository_name.replace('_', '-')
        ref = format.format(repository_name=dashed_repository_name, revision=revision)
        return Markup('<a class="link" href="%s">%s</a>' % (ref, repository_name))

    def decorate_revision(self, revision, repository_url):
        format = self._config.scm_browser_url_format
        if not format or not repository_url:
            return revision
        repository_name = repository_url.split('/')[-1].lower()
        dashed_repository_name = repository_name.replace('_', '-')
        ref = format.format(repository_name=dashed_repository_name, revision=revision)
        return Markup('<a class="link" href="%s">%s</a>' % (ref, revision))

    # limit list length to 'length' items
    def limit_count(self, value, length=None):
        if length is None:
            return value
        else:
            return value[:length]
