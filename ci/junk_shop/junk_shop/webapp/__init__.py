import os
import sys
import time
from pony.orm import sql_debug, OperationalError
from flask import Flask
from ..utils import DbConfig
from .. import models

app = Flask(__name__)

from . import filters
from . import views
from . import branch_views
from . import version_list_views
from . import metrics_views


def retry_on_db_error(fn, *args, **kw):
    while True:
        try:
            return fn(*args, **kw)
        except OperationalError as x:
            print >>sys.stderr, 'Error connecting to database:', x
            time.sleep(1)

def init():
    db_config = DbConfig.from_string(os.environ['DB_CONFIG'])
    if 'SQL_DEBUG' in os.environ:
        sql_debug(True)
    retry_on_db_error(models.db.bind, 'postgres', host=db_config.host,
                      user=db_config.user, password=db_config.password, port=db_config.port)
    retry_on_db_error(models.db.generate_mapping, create_tables=True)

init()
