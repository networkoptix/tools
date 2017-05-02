Database, pytest plugin and web frontend for storing and viewing test results


To store results to database in pytest run:
$ PYTHONPATH=$PYTHONPATH:$HOME/proj/test/pytest-db-plugin PYTEST_PLUGINS=junk_shop.pytest_plugin pytest --capture-db=postgres:xa2Db_45xd@localhost --nocapturelog

To select runs:
> select run.*, count(artifact) artifacts from run left outer join artifact on artifact.run = run.id group by run.id order by run.id;

