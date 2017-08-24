import datetime
import abc
from fnmatch import fnmatch
from functools import partial
from pony.orm import db_session, desc, select
from flask import render_template
from .. import models
from junk_shop.webapp import app
from .utils import format_bytes
from .filters import format_timedelta


# How many measured versions are taken to measure which server_count is to show
MERGE_DURATION_DYNAMICS_LAST_VERSION_COUNT = 60
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

    __metaclass__ = abc.ABCMeta

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return '<%s -> %s/%s>' % (self.x, self.y, self.text)

    @property
    @abc.abstractmethod
    def text(self):
        pass


class DurationPoint(Point):

    @property
    def text(self):
        if self.y is None:
            return None
        return format_timedelta(datetime.timedelta(seconds=self.y))


class BytesPoint(Point):

    @property
    def text(self):
        if self.y is None:
            return None
        return format_bytes(self.y)


class MetricTrace(object):

    def __init__(self, name, points, visible=True, yaxis=None, metric_name=None, use_lws=True):
        self.name = name
        self.points = points
        self.visible = visible
        self.yaxis = yaxis
        self.metric_name = metric_name
        self.use_lws = use_lws

    def __repr__(self):
        return '<%s use_lws=%r metric_name=%r points-len=%r>' % (self.name, self.use_lws, self.metric_name, len(self.points))


class RunParameter(object):

    def __init__(self, name, value_list):
        self.name = name
        self.value_list = value_list


# convert int parameters to int, leave rest ones as is
def param_to_int(value):
    try:
        return int(value)
    except ValueError:
        return value

def param_to_bool(value):
    return value in ['true', 'yes']

def fnmatch_list(name, pattern_list):
    for pattern in pattern_list:
        if fnmatch(name, pattern):
            return True
    return False

def load_branch_platform_version_run_parameters(branch_name, platform_name, version):
    parameters = {}  # name -> value set
    for (name, value) in select(
            (pv.run_parameter.name, pv.value)
            for run in models.Run for pv in run.run_parameters
            if run.version == version and
               run.branch.name == branch_name and
               run.platform.name == platform_name):
        parameters.setdefault(name, set()).add(param_to_int(value))
    return [RunParameter(name, sorted(values)) for name, values in parameters.items()]

def load_branch_platform_run_parameters(branch_name, platform_name):
    parameters = {}  # name -> value set
    for (name, value) in select(
            (pv.run_parameter.name, pv.value)
            for run in models.Run for pv in run.run_parameters
            if run.branch.name == branch_name and
               run.platform.name == platform_name):
        parameters.setdefault(name, set()).add(param_to_int(value))
    return [RunParameter(name, sorted(values)) for name, values in parameters.items()]

def load_branch_platform_version_metric_traces(branch_name, platform_name, version):
    all_metric_names = set()
    accumulators = {}
    for use_lws, server_count, metric_name, metric_value in select(
            (use_lws_param.value, server_count_param.value, mv.metric.name, mv.value)
            for mv in models.MetricValue
            for run in mv.run
            for use_lws_param in run.root_run.run_parameters
            for server_count_param in run.root_run.run_parameters
            if run.root_run.version == version and
               run.root_run.branch.name == branch_name and
               run.root_run.platform.name == platform_name and
               use_lws_param.run_parameter.name == 'use_lightweight_servers' and
               server_count_param.run_parameter.name == 'server_count'
            ):
        all_metric_names.add(metric_name)
        acc = accumulators.setdefault((param_to_bool(use_lws), int(server_count), metric_name), MetricAccumulator())
        acc.add_value(metric_value)
    for use_lws in [True, False]:
        for metric_name in all_metric_names:
            if metric_name == 'total_bytes_sent':
                Point = BytesPoint
                yaxis = 'y2'
            elif metric_name.startswith('host_memory_usage.'):
                Point = BytesPoint
                yaxis = None
            else:
                Point = DurationPoint
                yaxis = None
            points = [Point(server_count, acc.mean)
                          for (acc_use_lws, server_count, acc_metric_name), acc in sorted(accumulators.items())
                               if acc_use_lws == use_lws and acc_metric_name == metric_name]
            if fnmatch(metric_name, 'host_memory_usage.*.mediaserver'):
                visible = not use_lws
            elif fnmatch(metric_name, 'host_memory_usage.*.lws'):
                visible = use_lws
            else:
                visible = not fnmatch_list(metric_name, ['*_init_duration', 'host_memory_usage.*.used_swap'])
            trace_name = metric_name.replace('host_memory_usage.', '')
            yield MetricTrace(trace_name, points, visible, yaxis, metric_name=metric_name, use_lws=use_lws)

def load_branch_platform_metric_traces(branch_name, platform_name):
    all_server_counts = {}   # server_count -> collected metric count
    all_versions = set()
    accumulators = {}  # (metric_name, version, server_count) -> MetricAcculumator
    for metric_name, version, use_lws, server_count, metric_value in select(
            (mv.metric.name, run.root_run.version, use_lws_param.value, server_count_param.value, mv.value)
            for mv in models.MetricValue
            for run in mv.run
            for use_lws_param in run.root_run.run_parameters
            for server_count_param in run.root_run.run_parameters
            if run.root_run.branch.name == branch_name and
               run.root_run.platform.name == platform_name and
               use_lws_param.run_parameter.name == 'use_lightweight_servers' and
               server_count_param.run_parameter.name == 'server_count' and
               (mv.metric.name in ['merge_duration', 'total_bytes_sent'] or
                mv.metric.name.startswith('host_memory_usage.'))
            ):
        server_count = int(server_count)
        all_versions.add(version)
        all_server_counts[server_count] = all_server_counts.get(server_count, 0) + 1
        acc = accumulators.setdefault((metric_name, param_to_bool(use_lws), version, server_count), MetricAccumulator())
        acc.add_value(metric_value)
    versions = sorted(all_versions)[-MERGE_DURATION_DYNAMICS_LAST_VERSION_COUNT:]
    versions_set = set(versions)
    all_metrics = sorted(set(metric_name for metric_name, _, _, _ in accumulators))
    for use_lws in [True, False]:
        last_server_counts = {}
        for _, acc_use_lws, version, server_count in accumulators:
            if acc_use_lws == use_lws and version in versions_set:
                last_server_counts[server_count] = last_server_counts.get(server_count, 0) + 1
        # show greatest server counts from last runs, in descending order
        show_server_counts = sorted(last_server_counts, reverse=True)[:MAX_SERVER_COUNT_TRACES]
        for metric_name in all_metrics:
            for server_count in show_server_counts:
                if metric_name == 'merge_duration':
                    Point = DurationPoint
                else:
                    Point = BytesPoint
                point_list = []
                for version in versions:
                    acc = accumulators.get((metric_name, use_lws, version, server_count))
                    if acc:
                        value = acc.mean
                    else:
                        value = None
                    point_list.append(Point(version, value))
                trace_name = '%d servers' % server_count
                if metric_name.startswith('host_memory_usage.'):
                    trace_name += ' - ' + metric_name.replace('host_memory_usage.', '')
                visible = (not fnmatch(metric_name, 'host_memory_usage.*') or
                           fnmatch(metric_name, 'host_memory_usage.*.used') or
                           fnmatch(metric_name, 'host_memory_usage.*.total') and server_count == max(show_server_counts))
                yield MetricTrace(trace_name, point_list, visible, metric_name=metric_name, use_lws=use_lws)


@app.route('/branch/<branch_name>/<platform_name>/<version>/metrics')
@db_session
def branch_platform_version_metrics(branch_name, platform_name, version):

    def pred(trace, use_lws, is_memory_usage):
        return (trace.use_lws == use_lws and
                trace.metric_name.startswith('host_memory_usage.') == is_memory_usage)

    trace_list = list(load_branch_platform_version_metric_traces(branch_name, platform_name, version))
    lws_traces = dict(
        merge_duration=filter(partial(pred, use_lws=True, is_memory_usage=False), trace_list),
        host_memory_usage=filter(partial(pred, use_lws=True, is_memory_usage=True), trace_list),
        )
    full_traces = dict(
        merge_duration=filter(partial(pred, use_lws=False, is_memory_usage=False), trace_list),
        host_memory_usage=filter(partial(pred, use_lws=False, is_memory_usage=True), trace_list),
        )
    run_parameters = load_branch_platform_version_run_parameters(branch_name, platform_name, version)
    return render_template(
        'branch_platform_version_metrics.html',
        branch_name=branch_name,
        platform_name=platform_name,
        version=version,
        lws_traces=lws_traces,
        full_traces=full_traces,
        run_parameters=run_parameters,
        )

@app.route('/branch/<branch_name>/<platform_name>/metrics')
@db_session
def branch_platform_metrics(branch_name, platform_name):

    def pred(trace, use_lws, is_total_bytes_sent, is_memory_usage):
        return (trace.use_lws == use_lws and
                (trace.metric_name == 'total_bytes_sent') == is_total_bytes_sent and
                trace.metric_name.startswith('host_memory_usage.') == is_memory_usage)

    trace_list = list(load_branch_platform_metric_traces(branch_name, platform_name))
    lws_traces = dict(
        merge_duration=filter(partial(pred, use_lws=True, is_total_bytes_sent=False, is_memory_usage=False), trace_list),
        total_bytes_sent=filter(partial(pred, use_lws=True, is_total_bytes_sent=True, is_memory_usage=False), trace_list),
        memory_usage=filter(partial(pred, use_lws=True, is_total_bytes_sent=False, is_memory_usage=True), trace_list),
        )
    full_traces = dict(
        merge_duration=filter(partial(pred, use_lws=False, is_total_bytes_sent=False, is_memory_usage=False), trace_list),
        total_bytes_sent=filter(partial(pred, use_lws=False, is_total_bytes_sent=True, is_memory_usage=False), trace_list),
        memory_usage=filter(partial(pred, use_lws=False, is_total_bytes_sent=False, is_memory_usage=True), trace_list),
        )
    run_parameters = load_branch_platform_run_parameters(branch_name, platform_name)
    return render_template(
        'branch_platform_metrics.html',
        branch_name=branch_name,
        platform_name=platform_name,
        lws_traces=lws_traces,
        full_traces=full_traces,
        run_parameters=run_parameters,
        )
