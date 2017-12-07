'load and render templates'

import logging
import os.path

import jinja2

from junk_shop.filters import JinjaFilters

log = logging.getLogger(__name__)


PROJECTS_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(PROJECTS_DIR, 'templates')


class TemplateRenderer(object):

    def __init__(self, services_config):
        loader = jinja2.FileSystemLoader(TEMPLATES_DIR)
        self._env = jinja2.Environment(loader=loader)
        self._junk_shop_url = services_config.junk_shop_url
        self._filters = JinjaFilters(services_config)
        self._filters.install(self._env)
        self._env.globals['url_for'] = self.url_for

    def render(self, template_path, **kw):
        template = self._env.get_template(template_path)
        return template.render(**kw)

    def url_for(self, endpoint, **values):
        if endpoint == 'artifact':
            artifact_id = values['artifact_id']  # required keyword
            return '{}/artifact/{}'.format(self._junk_shop_url, artifact_id)
        if endpoint == 'run':
            run_id = values['run_id']  # required keyword
            anchor = values.get('_anchor')  # optional
            if anchor:
                return '{}/run/{}#{}'.format(self._junk_shop_url, run_id, anchor)
            else:
                return '{}/run/{}'.format(self._junk_shop_url, run_id)
        assert False, repr(endpoint)  # Unsupported endpoint
