"""
    fail_stats_views.py
    ~~~~~~~~~~~~~~~~~~~
    A view for statistic of build stage fails.
"""

from flask_wtf import FlaskForm
from wtforms import SelectField, DateField, validators, ValidationError
from .utils import paginator,  STAGES
from pony.orm import db_session, select, count, desc, max
from datetime import timedelta, datetime
from flask import render_template, request
from junk_shop.webapp import app
from .. import models

FROM_TIMEDELTA = timedelta(days=7)
DATETIME_FORM_FORMAT = '%Y %b %d'
FAILED_TESTS_PAGE_SIZE = 30


def datetime_from_request_str(datetime_str):
    if datetime_str is None:
        return None
    return datetime.strptime(datetime_str, '%Y-%m-%d').date()


class FailStatsForm(FlaskForm):
    """
        A Flask WTForm to select statistic of fails by
        `project`, `branch`, `platform` and `test_bundle` (units, functional, etc)
        Flask bootstrap (https://pythonhosted.org/Flask-Bootstrap/forms.html) is used for rendering the form.
    """
    project = SelectField('Project', coerce=int)
    branch = SelectField('Branch', coerce=int)
    platform = SelectField('Platform', coerce=int)
    test_bundle = SelectField('Test bundle', coerce=int)
    # momentjs is used to implement datetimepicker
    #
    # Sample of implementation - https://gist.github.com/miguelgrinberg/5a1b3749dbe1bb254ff7a41e59cf04c9
    date_from = DateField(
        'From', validators=[validators.data_required()], default=datetime.now() - FROM_TIMEDELTA,
        id='datefrom', format=DATETIME_FORM_FORMAT)
    date_to = DateField(
        'To', validators=[validators.data_required()], default=datetime.now(), id='dateto',
        format=DATETIME_FORM_FORMAT)

    def validate_date_from(form, field):
        if field.data > form.date_to.data:
            raise ValidationError('From date should be younger than To')

    def validate_date_to(form, field):
        if field.data < form.date_from.data:
            raise ValidationError('To date should be elder than From')


@app.route('/fails', methods=['GET', 'POST'])
@db_session
def fail_stats():
    page = int(request.args.get('page', 1))

    page_size = FAILED_TESTS_PAGE_SIZE
    # Create form
    form = FailStatsForm(request.form)
    form.project.choices = [(project.id, project.name) for project in models.Project.select()
                            if project.name in ['ci', 'release']]
    form.branch.choices = [(branch.id, branch.name) for branch in models.Branch.select()]
    form.platform.choices = [(platform.id, platform.name) for platform in models.Platform.select()
                             if platform.name in ['linux-x64', 'windows-x64', 'mac']]
    form.test_bundle.choices = [(test.id, test.path) for test in models.Test.select()
                                if test.path in STAGES]

    if request.method == 'GET':
        # Initialize form values
        form_field_values = [
            (form.date_from, datetime_from_request_str(request.args.get('date_from', None))),
            (form.date_to, datetime_from_request_str(request.args.get('date_to', None))),
            (form.branch, int(request.args.get('branch', 0))),
            (form.project, int(request.args.get('project', 0))),
            (form.platform, int(request.args.get('platform', 0))),
            (form.test_bundle, int(request.args.get('bundle', 0)))]

        def set_form_field_value(field, value):
            if value:
                field.data = value
                return True
            return False

        set_fields_count = [
            set_form_field_value(field, value)
            for field, value in form_field_values].count(True)

        if set_fields_count != len(form_field_values):
            return render_template(
                'fail_stats.html',
                total_records=0,
                form=form)

    elif request.method == 'POST':
        page = 1
        if not form.validate():
            return render_template(
                'fail_stats.html',
                total_records=0,
                form=form)

    # Select tests
    query = select(
        (r.test.path, r.test.id, count(r), max(r.root_run.id), max(r.id),
         max(r.root_run.build.build_num)) for r in models.Run
        if (r.started_at >= form.date_from.data and
            r.started_at <= form.date_to.data + timedelta(days=1) and
            r.root_run.platform.id == form.platform.data and
            r.root_run.build.project.id == form.project.data and
            r.root_run.build.branch.id == form.branch.data and
            r.root_run.test.id == form.test_bundle.data and
            r.test.is_leaf and

            r.outcome == 'failed'))

    rec_count = query.count()

    failed_tests = [r for r in query.order_by(desc(3)).page(page, page_size)]

    return render_template(
        'fail_stats.html',
        paginator=paginator(page, rec_count, page_size),
        project=dict(form.project.choices).get(form.project.data),
        branch=dict(form.branch.choices).get(form.branch.data),
        form=form,
        total_records=rec_count,
        failed_tests=failed_tests)
