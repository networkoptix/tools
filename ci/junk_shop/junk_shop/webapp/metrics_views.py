import datetime
from pony.orm import db_session, desc, select
from flask import render_template
from .. import models
from junk_shop.webapp import app


# How many measured versions are taken to measure which server_count is to show
MERGE_DURATION_DYNAMICS_LAST_VERSION_COUNT = 20
# How many server count traces to show in merge time dynamics graph
MAX_SERVER_COUNT_TRACES = 6


# There could be several runs with same server_count parameters for requested version/build.
# We show mean values for each metrics.
class MetricAccumulator(object):

    def __init__(self):
        self.count = 0
        self.sum = 0

    def add_value(self, value):
        self.count += 1
        self.sum += value

    @property
    def mean(self):
        if self.count:
            return self.sum / self.count
        else:
            return 0


class Point(object):

    def __init__(self, x, y, text=None):
        self.x = x
        self.y = y
        self.text = text or y

    def __repr__(self):
        return '<%s -> %s/%s>' % (self.x, self.y, self.text)


class MetricTrace(object):

    def __init__(self, metric_name, points):
        self.name = metric_name
        self.points = points

    def __repr__(self):
        return '<%s: %r>' % (self.name, self.points)


def load_branch_platform_version_metric_traces(branch_name, platform_name, version):
    all_metric_names = set()
    accumulators = {}
    for server_count, metric_name, metric_value in select(
            (param.value, mv.metric.name, mv.value)
            for mv in models.MetricValue
            for run in mv.run
            for param in run.root_run.run_parameters
            if run.root_run.version == version and
               run.root_run.branch.name == branch_name and
               run.root_run.platform.name == platform_name and
               param.run_parameter.name == 'server_count'
            ):
        all_metric_names.add(metric_name)
        acc = accumulators.setdefault((int(server_count), metric_name), MetricAccumulator())
        acc.add_value(metric_value)
        # print 'metric:', server_count, metric_name, metric_value
    for metric_name in all_metric_names:
        points = [Point(server_count, acc.mean, datetime.timedelta(seconds=acc.mean))
                      for (server_count, acc_metric_name), acc in sorted(accumulators.items())
                           if acc_metric_name == metric_name]
        yield MetricTrace(metric_name, points)

def load_branch_platform_metric_traces(branch_name, platform_name):
    metric_name = 'merge_duration'
    all_server_counts = {}   # server_count -> collected metric count
    versions = set()
    accumulators = {}
    for version, server_count, metric_value in select(
            (run.root_run.version, param.value, mv.value)
            for mv in models.MetricValue
            for run in mv.run
            for param in run.root_run.run_parameters
            if run.root_run.branch.name == branch_name and
               run.root_run.platform.name == platform_name and
               param.run_parameter.name == 'server_count' and
               mv.metric.name == metric_name
            ):
        server_count = int(server_count)
        versions.add(version)
        all_server_counts[server_count] = all_server_counts.get(server_count, 0) + 1
        acc = accumulators.setdefault((version, server_count), MetricAccumulator())
        acc.add_value(metric_value)
        # print 'metric:', version, server_count, metric_value
    ## print 'all counts', sorted(all_server_counts.items())
    last_versions = set(sorted(versions)[-MERGE_DURATION_DYNAMICS_LAST_VERSION_COUNT:])
    ## print 'last versions:', sorted(last_versions)
    last_server_counts = {}
    for version, server_count in accumulators:
        if version in last_versions:
            last_server_counts[server_count] = last_server_counts.get(server_count, 0) + 1
    ## print 'last counts', sorted(last_server_counts.items())
    # show greatest server counts from last runs
    show_server_counts = sorted(last_server_counts)[-MAX_SERVER_COUNT_TRACES:]
    ## print 'show_server_counts:', show_server_counts
    for server_count in show_server_counts:
        points = [Point(version, acc.mean, datetime.timedelta(seconds=acc.mean))
                      for (version, acc_server_count), acc in sorted(accumulators.items())
                      if acc_server_count == server_count]
        yield MetricTrace('%d servers' % server_count, points)


@app.route('/branch/<branch_name>/<platform_name>/<version>/metrics')
@db_session
def branch_platform_version_metrics(branch_name, platform_name, version):
    trace_list = list(load_branch_platform_version_metric_traces(branch_name, platform_name, version))
    return render_template(
        'branch_platform_version_metrics.html',
        branch_name=branch_name,
        platform_name=platform_name,
        version=version,
        trace_list=trace_list,
        )

@app.route('/branch/<branch_name>/<platform_name>/metrics')
@db_session
def branch_platform_metrics(branch_name, platform_name):
    trace_list = list(load_branch_platform_metric_traces(branch_name, platform_name))
    return render_template(
        'branch_platform_metrics.html',
        branch_name=branch_name,
        platform_name=platform_name,
        trace_list=trace_list,
        )
