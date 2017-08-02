from flask import request, render_template
from pony.orm import db_session, select, count, desc, raw_sql
from .. import models
from .utils import DEFAULT_RUN_LIST_PAGE_SIZE
from junk_shop.webapp import app



class TestsRec(object):

    def __init__(self, run):
        self.run = run  # models.Run
        self.test_count = {}  # outcome:str -> count:int


class VersionRec(object):

    def __init__(self, version):
        self.version = version  # str
        self.started_at = None  # or datetime
        self.build = None       # TestsRec
        self.unit = None        # TestsRec
        self.functional = None  # TestsRec
        self.has_scalability = False


def load_test_outcomes(branch_name, platform_name, version_list, version_map):
    version_str_list = [rec.version for rec in version_list]
    for root_run, test_path, outcome, count in select(
            (root_run, root_run.test.path, test_run.outcome, count(test_run))
            for root_run in models.Run for test_run in models.Run
            if (test_run.root_run is root_run or test_run is root_run) and
               root_run.branch.name == branch_name and root_run.platform.name == platform_name and
               root_run.version in version_str_list and
               (test_run.test.path.startswith('unit') or
                test_run.test.path.startswith('functional') or
                test_run.test.path.startswith('build')) and
                test_run.test.is_leaf):
        version_rec = version_map[root_run.version]
        test = test_path.split('/')[0]
        tests_rec = getattr(version_rec, test)
        if not tests_rec:
            tests_rec = TestsRec(root_run)
            setattr(version_rec, test, tests_rec)
        tests_rec.test_count[outcome] = count
        if test == 'build':
            version_rec.started_at = root_run.started_at


def load_has_scalability_flags(branch_name, platform_name, version_list, version_map):
    version_str_list = [rec.version for rec in version_list]
    for version, count in select(
            (run.root_run.version, count(run.metrics))
            for run in models.Run
            if run.root_run.branch.name == branch_name and run.root_run.platform.name == platform_name and
               run.root_run.version in version_str_list and
               run.test.path.startswith('functional/scalability_test.py') and run.test.is_leaf):
        if count > 0:
            version_rec = version_map[version]
            version_rec.has_scalability = True


@app.route('/branch/<branch_name>/<platform_name>/')
@db_session
def branch_platform_version_list(branch_name, platform_name):
    page = int(request.args.get('page', 1))
    page_size = DEFAULT_RUN_LIST_PAGE_SIZE
    query = select(
        (run.version, raw_sql("string_to_array(run.version, '.')::int[]"))
        for run in models.Run
        if run.root_run is None and
        run.branch.name == branch_name and
        run.platform.name == platform_name)
    version_list = [VersionRec(version) for (version, _) in
                        query.order_by(desc(2)).page(page, page_size)]
    version_map = {rec.version: rec for rec in version_list}
    rec_count = query.count()
    page_count = (rec_count - 1) / page_size + 1
    load_test_outcomes(branch_name, platform_name, version_list, version_map)
    load_has_scalability_flags(branch_name, platform_name, version_list, version_map)
    return render_template(
        'branch_platform_version_list.html',
        current_page=page,
        page_count=page_count,
        branch_name=branch_name,
        platform_name=platform_name,
        version_list=version_list)
