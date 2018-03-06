import datetime
import abc
from fnmatch import fnmatch
from functools import partial
from pony.orm import db_session, desc, select
from flask import render_template
from ..utils import param_to_bool, timedelta_to_str
from .. import models
from junk_shop.webapp import app
from .utils import format_bytes


# How many measured builds are taken to measure which server_count is to show
MERGE_DURATION_DYNAMICS_LAST_BUILD_COUNT = 60
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
        return timedelta_to_str(datetime.timedelta(seconds=self.y))


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


def fnmatch_list(name, pattern_list):
    for pattern in pattern_list:
        if fnmatch(name, pattern):
            return True
    return False


def load_branch_platform_build_run_parameters(project_name, branch_name, build_num, platform_name):
    parameters = {}  # name -> value set
    for (name, value) in select(
            (pv.run_parameter.name, pv.value)
            for run in models.Run for pv in run.run_parameters
            if run.build.project.name == project_name and
               run.build.branch.name == branch_name and
               run.build.build_num == build_num and
               run.platform.name == platform_name):
        parameters.setdefault(name, set()).add(param_to_int(value))
    return [RunParameter(name, sorted(values)) for name, values in parameters.items()]

def load_branch_platform_run_parameters(project_name, branch_name, platform_name):
    parameters = {}  # name -> value set
    for (name, value) in select(
            (pv.run_parameter.name, pv.value)
            for run in models.Run for pv in run.run_parameters
            if run.build.project.name == project_name and
               run.build.branch.name == branch_name and
               run.platform.name == platform_name):
        parameters.setdefault(name, set()).add(param_to_int(value))
    return [RunParameter(name, sorted(values)) for name, values in parameters.items()]


# branch/platform/build page  =====================================================================

def load_build_platform_metrics(project_name, branch_name, build_num, platform_name):
    accumulators = {}
    for use_lws, server_count, metric_name, metric_value in select(
            (use_lws_param.value, server_count_param.value, mv.metric.name, mv.value)
            for mv in models.MetricValue
            for run in mv.run
            for use_lws_param in run.root_run.run_parameters
            for server_count_param in run.root_run.run_parameters
            if run.root_run.build.project.name == project_name and
               run.root_run.build.branch.name == branch_name and
               run.root_run.build.build_num == build_num and
               run.root_run.platform.name == platform_name and
               use_lws_param.run_parameter.name == 'use_lightweight_servers' and
               server_count_param.run_parameter.name == 'server_count'
            ):
        acc = accumulators.setdefault((param_to_bool(use_lws), int(server_count), metric_name), MetricAccumulator())
        acc.add_value(metric_value)
    return accumulators

def generate_branch_platform_build_traces(accumulators):
    all_metric_names = sorted(set(metric_name for _, _, metric_name in accumulators))
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
            if fnmatch(metric_name, 'host_memory_usage.*'):
                if use_lws:
                    visible = not fnmatch_list(metric_name, ['host_memory_usage.*.mediaserver', 'host_memory_usage.*.used_swap'])
                else:
                    visible = fnmatch_list(metric_name, ['host_memory_usage.*.total', 'host_memory_usage.*.mediaserver'])
            else:
                visible = not fnmatch(metric_name, '*_init_duration')
            trace_name = metric_name.replace('host_memory_usage.', '')
            yield MetricTrace(trace_name, points, visible, yaxis, metric_name=metric_name, use_lws=use_lws)

def load_branch_platform_build_metric_traces(project_name, branch_name, build_num, platform_name):

    def pred(use_lws, is_memory_usage, trace):
        if not use_lws and trace.metric_name == 'total_bytes_sent': return False
        return (trace.use_lws == use_lws and
                trace.metric_name.startswith('host_memory_usage.') == is_memory_usage)

    accumulators = load_build_platform_metrics(project_name, branch_name, build_num, platform_name)
    trace_list = list(generate_branch_platform_build_traces(accumulators))
    lws_traces = dict(
        has_total_bytes_sent=True,
        merge_duration=filter(partial(pred, True, False), trace_list),
        host_memory_usage=filter(partial(pred, True, True), trace_list),
        )
    full_traces = dict(
        has_total_bytes_sent=False,
        merge_duration=filter(partial(pred, False, False), trace_list),
        host_memory_usage=filter(partial(pred, False, True), trace_list),
        )
    return (lws_traces, full_traces)

@app.route('/branch/<project_name>/<branch_name>/<build_num>/<platform_name>/metrics')
@db_session
def build_platform_metrics(project_name, branch_name, build_num, platform_name):
    lws_traces, full_traces = load_branch_platform_build_metric_traces(project_name, branch_name, build_num, platform_name)
    run_parameters = load_branch_platform_build_run_parameters(project_name, branch_name, build_num, platform_name)
    return render_template(
        'build_platform_metrics.html',
        project_name=project_name,
        branch_name=branch_name,
        build_num=build_num,
        platform_name=platform_name,
        lws_traces=lws_traces,
        full_traces=full_traces,
        run_parameters=run_parameters,
        )


# branch/platform page  =============================================================================

def load_branch_platform_metrics(project_name, branch_name, platform_name):
    accumulators = {}  # (metric_name, build_num, server_count) -> MetricAcculumator
    for metric_name, build_num, use_lws, server_count, metric_value in select(
            (mv.metric.name, run.root_run.build.build_num, use_lws_param.value, server_count_param.value, mv.value)
            for mv in models.MetricValue
            for run in mv.run
            for use_lws_param in run.root_run.run_parameters
            for server_count_param in run.root_run.run_parameters
            if run.root_run.build.project.name == project_name and
               run.root_run.build.branch.name == branch_name and
               run.root_run.platform.name == platform_name and
               use_lws_param.run_parameter.name == 'use_lightweight_servers' and
               server_count_param.run_parameter.name == 'server_count' and
               (mv.metric.name in ['merge_duration', 'total_bytes_sent'] or
                mv.metric.name.startswith('host_memory_usage.'))
            ):
        server_count = int(server_count)
        acc = accumulators.setdefault((metric_name, param_to_bool(use_lws), build_num, server_count), MetricAccumulator())
        acc.add_value(metric_value)
    return accumulators

def generate_branch_platform_traces(accumulators):
    all_build_nums = set(build_num for _, _, build_num, _ in accumulators)
    build_nums = sorted(all_build_nums)[-MERGE_DURATION_DYNAMICS_LAST_BUILD_COUNT:]
    build_nums_set = set(build_nums)
    all_metrics = sorted(set(metric_name for metric_name, _, _, _ in accumulators))
    for use_lws in [True, False]:
        last_server_counts = {}
        for _, acc_use_lws, build_num, server_count in accumulators:
            if acc_use_lws == use_lws and build_num in build_nums_set:
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
                for build_num in build_nums:
                    acc = accumulators.get((metric_name, use_lws, build_num, server_count))
                    if acc:
                        value = acc.mean
                    else:
                        value = None
                    point_list.append(Point(build_num, value))
                trace_name = '%d servers' % server_count
                if metric_name.startswith('host_memory_usage.'):
                    trace_name += ' - ' + metric_name.replace('host_memory_usage.', '')
                visible = (not fnmatch(metric_name, 'host_memory_usage.*') or
                           fnmatch(metric_name, 'host_memory_usage.*.used') or
                           fnmatch(metric_name, 'host_memory_usage.*.total') and server_count == max(show_server_counts))
                yield MetricTrace(trace_name, point_list, visible, metric_name=metric_name, use_lws=use_lws)


@app.route('/project/<project_name>/<branch_name>/<platform_name>/metrics')
@db_session
def branch_platform_metrics(project_name, branch_name, platform_name):

    def pred(use_lws, is_total_bytes_sent, is_memory_usage, trace):
        return (trace.use_lws == use_lws and
                (trace.metric_name == 'total_bytes_sent') == is_total_bytes_sent and
                trace.metric_name.startswith('host_memory_usage.') == is_memory_usage)

    accumulators = load_branch_platform_metrics(project_name, branch_name, platform_name)
    trace_list = list(generate_branch_platform_traces(accumulators))
    lws_traces = dict(
        merge_duration=filter(partial(pred, True, False, False), trace_list),
        total_bytes_sent=filter(partial(pred, True, True, False), trace_list),
        memory_usage=filter(partial(pred, True, False, True), trace_list),
        )
    full_traces = dict(
        merge_duration=filter(partial(pred, False, False, False), trace_list),
        memory_usage=filter(partial(pred, False, False, True), trace_list),
        )
    run_parameters = load_branch_platform_run_parameters(project_name, branch_name, platform_name)
    return render_template(
        'branch_platform_metrics.html',
        project_name=project_name,
        branch_name=branch_name,
        platform_name=platform_name,
        lws_traces=lws_traces,
        full_traces=full_traces,
        run_parameters=run_parameters,
        )
