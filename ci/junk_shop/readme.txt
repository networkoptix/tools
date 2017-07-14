Database, pytest plugin and web frontend for storing and viewing test results


To store results to database in pytest run:
$ PYTHONPATH=$PYTHONPATH:$HOME/proj/test/pytest-db-plugin PYTEST_PLUGINS=junk_shop.pytest_plugin pytest --capture-db=postgres:xa2Db_45xd@localhost --nocapturelog

To select runs:
> select run.*, count(artifact) artifacts from run left outer join artifact on artifact.run = run.id group by run.id order by run.id desc limit 60;

To run web application locally, for development:
cd ~/develop/devtools/ci/junkshop
PYTHONPATH=. DB_CONFIG=postgres:<postgress-db-password>@localhost FLASK_APP=junk_shop.webapp flask run

To do the same, but when postgres database is behind double-ssh:
ssh -L 15432:localhost:5432 junk-shop  &  # where 'junk-shop' is remote ssh host
PYTHONPATH=. DB_CONFIG=postgres:<postgress-db-password>@localhost:15432 FLASK_APP=junk_shop.webapp FLASK_DEBUG=1 flask run
