import os
import sys
import time
import threading

from pony.orm import set_sql_debug, OperationalError
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect

from ..filters import JinjaFilters
from .. import models


class FlaskApp(Flask):

    def __init__(self, *args, **kw):
        super(FlaskApp, self).__init__(*args, **kw)
        self._load_settings()
        self._init_filters()
        self._set_sql_debug()
        self.before_request(self._set_sql_debug)
        self._init_db()
        CSRFProtect(self)
        Bootstrap(self)

    def _load_settings(self):
        self.config.from_object('junk_shop.webapp.default_config')
        if 'JUNK_SHOP_SETTINGS' in os.environ:
            self.config.from_envvar('JUNK_SHOP_SETTINGS')

    def _set_sql_debug(self):
        set_sql_debug(
            self.config['SQL_DEBUG'] or 'SQL_DEBUG' in os.environ,
            show_values='SQL_DEBUG_VALUES' in os.environ)

    # our container may be started before db, must wait until it is available
    def _retry_on_db_error(self, fn, *args, **kw):
        while True:
            try:
                return fn(*args, **kw)
            except OperationalError as x:
                print >>sys.stderr, 'Error connecting to database:', x
                time.sleep(1)

    def _init_db(self):
        pg_password = os.environ['PGPASSWORD']
        self._retry_on_db_error(
            models.db.bind,
            'postgres',
            host=self.config['DB_HOST'],
            user=self.config['DB_USER'],
            password=pg_password,
            port=self.config['DB_PORT'],
            )
        self._retry_on_db_error(models.db.generate_mapping, create_tables=True)


    def _init_filters(self):
        filters_config = JinjaFilters.Config(
            self.config.get('JIRA_URL'),
            self.config.get('SCM_BROWSER_URL_FORMAT'),
            )
        filters = JinjaFilters(filters_config)
        filters.install(self.jinja_env)


# modules imported below are using this variable
app = FlaskApp(__name__)


from . import commands
from . import robots_views
from . import views
from . import project_views
from . import build_views
from . import run_views
from . import metrics_views
from . import fail_stats_views
