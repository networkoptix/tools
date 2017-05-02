from datetime import datetime
import pytz
import tzlocal
from pony.orm import *
from junk_shop.models import *


def as_local_tz(dt):
    tz = tzlocal.get_localzone()
    return dt.astimezone(tz)


# select run.*, count(artifact) artifacts from run left outer join artifact on artifact.run = run.id group by run.id order by run.id;

@db_session
def dump():
    for artifact in select(artifact for artifact in Artifact).order_by(Artifact.id):
        print '-----', artifact.run.path, artifact.run.name, artifact.type.name, '-'*50
        print artifact.data
    print '-'*100

def main():
    db.bind('postgres', host='localhost', user='postgres', password='xa2Db_45xd')
    db.generate_mapping(create_tables=True)
    dump()

main()
