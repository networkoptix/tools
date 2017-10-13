import os
import sys
import time
from pony.orm import sql_debug, OperationalError
from flask import Flask
from .. import models

app = Flask(__name__)

app.config.from_object('junk_shop.webapp.default_config')
if 'JUNK_SHOP_SETTINGS' in os.environ:
    app.config.from_envvar('JUNK_SHOP_SETTINGS')

from . import filters
from . import views
from . import project_views
from . import build_views
from . import run_views
from . import branch_views
from . import version_list_views
from . import metrics_views


# our container may be started before db, must wait until it is available
def retry_on_db_error(fn, *args, **kw):
    while True:
        try:
            return fn(*args, **kw)
        except OperationalError as x:
            print >>sys.stderr, 'Error connecting to database:', x
            time.sleep(1)

def init():
    pg_password = os.environ['PGPASSWORD']
    sql_debug(app.config['SQL_DEBUG'])
    retry_on_db_error(models.db.bind, 'postgres',
                      host=app.config['DB_HOST'],
                      user=app.config['DB_USER'],
                      password=pg_password,
                      port=app.config['DB_PORT'])
    retry_on_db_error(models.db.generate_mapping, create_tables=True)

init()
