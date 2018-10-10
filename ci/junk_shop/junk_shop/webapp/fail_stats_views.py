"""
    fail_stats_views.py
    ~~~~~~~~~~~~~~~~~~~
    A view for statistic of build stage fails.
"""

from collections import namedtuple
from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, validators, ValidationError
from .utils import paginator, STAGE_NAMES, TESTED_PLATFORMS
from pony.orm import db_session, select, count, desc, max
from datetime import timedelta, datetime
from flask import render_template, request
from junk_shop.webapp import app
from .. import models

FROM_TIMEDELTA = timedelta(days=7)
DATETIME_FORM_FORMAT = '%Y %b %d'
FAILED_TESTS_PAGE_SIZE = 30
DEFAULT_BRANCH = 'default'
DEFAULT_PROJECT = 'ci'
DEFAULT_BUNDLE = 'unit'


def datetime_from_request_str(datetime_str, default=None):
    if datetime_str is None:
        return default
    return datetime.strptime(datetime_str, '%Y-%m-%d').date()


FailedTestRecord = namedtuple(
    'FailedTestRecord',
    [
        'path',
        'test_id',
        'fail_count',
        'last_root_run_id',
        'last_run_id',
        'last_build_num',
        'last_fail_timestamp',
    ])


class FailStatsForm(FlaskForm):
    """
        A Flask WTForm to select statistic of fails by
        `project`, `branch`, `platform` and `test_bundle` (units, functional, etc)
        Flask bootstrap (https://pythonhosted.org/Flask-Bootstrap/forms.html) is used for rendering the form.
    """
    project = SelectField('Project')
    branch = SelectField('Branch')
    platform = SelectField('Platform')
    test_bundle = SelectField('Test bundle')
    # momentjs is used to implement datetimepicker
    #
    # Sample of implementation - https://gist.github.com/miguelgrinberg/5a1b3749dbe1bb254ff7a41e59cf04c9
    date_from = DateField(
        'From',
        validators=[validators.data_required()],
        default=datetime.now() - FROM_TIMEDELTA,
        id='datefrom',
        format=DATETIME_FORM_FORMAT)
    date_to = DateField(
        'To',
        validators=[validators.data_required()],
        default=datetime.now(),
        id='dateto',
        format=DATETIME_FORM_FORMAT)

    def validate_date_from(form, field):
        if field.data > form.date_to.data:
            raise ValidationError('From date should be younger than To')

    def validate_date_to(form, field):
        if field.data < form.date_from.data:
            raise ValidationError('To date should be elder than From')

    def _prepare_and_check_get_form(self, request):
        """Initialize form values from `request` and check all values are set"""
        form_field_values = [
            (self.date_from,
             datetime_from_request_str(
                 request.args.get('date_from', None),
                 datetime.now() - FROM_TIMEDELTA)),
            (self.date_to,
             datetime_from_request_str(
                 request.args.get('date_to', None),
                 datetime.now())),
            (self.branch, request.args.get('branch', DEFAULT_BRANCH)),
            (self.project, request.args.get('project', DEFAULT_PROJECT)),
            (self.platform, request.args.get('platform')),
            (self.test_bundle, request.args.get('bundle', DEFAULT_BUNDLE))]

        def set_form_field_value(field, value):
            if value:
                field.data = value
                return True
            return False

        set_fields_count = [
            set_form_field_value(field, value)
            for field, value in form_field_values].count(True)

        if set_fields_count != len(form_field_values):
            return False
        return True

    def prepare_and_check_form(self, request):
        if request.method == 'POST':
            return self.validate()
        return self._prepare_and_check_get_form(request)


@app.route('/fails', methods=['GET', 'POST'])
@db_session
def fail_stats():
    page_size = FAILED_TESTS_PAGE_SIZE
    # Create form
    form = FailStatsForm(request.form)

    form.project.choices = [
        (project.name, project.name)
        for project in models.Project.select()
        if project.name in ['ci', 'release']
    ]
    form.branch.choices = [
        (branch.name, branch.name)
        for branch in models.Branch.select()
    ]
    form.platform.choices = [
        (platform.name, platform.name)
        for platform in models.Platform.select()
        if platform.name in TESTED_PLATFORMS
    ]
    form.test_bundle.choices = [
        (test.path, test.path)
        for test in models.Test.select()
        if test.path in STAGE_NAMES
    ]

    page = int(request.args.get('page', 1))

    if request.method == 'POST':
        page = 1

    if not form.prepare_and_check_form(request):
        return render_template(
            'fail_stats.html',
            total_records=0,
            form=form,
        )

    # Select tests
    query = select(
        (run.test.path,
         run.test.id,
         count(run),
         max(run.root_run.id),
         max(run.id),
         max(run.root_run.build.build_num),
         max(run.started_at))
        for run in models.Run
        if (run.root_run.started_at >= form.date_from.data and
            run.root_run.started_at <= form.date_to.data + timedelta(days=1) and
            run.root_run.platform.name == form.platform.data and
            run.root_run.build.project.name == form.project.data and
            run.root_run.build.branch.name == form.branch.data and
            run.root_run.test.path == form.test_bundle.data and
            run.test.is_leaf and run.outcome == 'failed'))

    rec_count = query.count()

    failed_tests = [
        FailedTestRecord(*test_record)
        for test_record in query.order_by(desc(3)).page(page, page_size)]

    return render_template(
        'fail_stats.html',
        paginator=paginator(page, rec_count, page_size),
        form=form,
        total_records=rec_count,
        failed_tests=failed_tests,
    )
