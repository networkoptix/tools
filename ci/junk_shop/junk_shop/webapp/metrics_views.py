import datetime
from pony.orm import db_session, desc, select
from flask import render_template
from .. import models
from junk_shop.webapp import app

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


class MetricTrace(object):

    def __init__(self, accumulators, trace_metric_name):
        self.name = trace_metric_name
        self.x = []
        self.y = []
        self.text = []
        for (server_count, metric_name), acc in sorted(accumulators.items()):
            if metric_name != trace_metric_name: continue
            self.x.append(server_count)
            self.y.append(acc.mean)
            self.text.append(datetime.timedelta(seconds=acc.mean))

    def __repr__(self):
        return '<%s: %r -> %r / %r>' % (self.name, self.x, self.y, self.text)


def load_metric_traces(branch_name, platform_name, version):
    all_metric_names = set()
    accumulators = {}
    for server_count, metric_name, metric_value in select(
            (p.value, m.metric.name, m.value)
            for m in models.MetricValue
            for r in m.run
            for p in r.root_run.run_parameters
            if r.root_run.version == version and
               r.root_run.branch.name == branch_name and
               r.root_run.platform.name == platform_name and
               p.run_parameter.name == 'server_count'
            ):
        all_metric_names.add(metric_name)
        acc = accumulators.setdefault((int(server_count), metric_name), MetricAccumulator())
        acc.add_value(metric_value)
        print server_count, metric_name, metric_value
    return [MetricTrace(accumulators, metric_name) for metric_name in all_metric_names]


@app.route('/branch/<branch_name>/<platform_name>/<version>/metrics')
@db_session
def branch_platform_version_metrics(branch_name, platform_name, version):
    trace_list = load_metric_traces(branch_name, platform_name, version)
    print trace_list
    return render_template(
        'branch_platform_version_metrics.html',
        branch_name=branch_name,
        platform_name=platform_name,
        version=version,
        trace_list=trace_list,
        )
