#!/usr/bin/env python
"""
make_html_build_report
~~~~~~~~~~~~~~~~~~~~~~

It's a script to get Junkshop build report in HTML format.
"""
import argparse
from junk_shop import TemplateRenderer, BuildInfoLoader, models
from junk_shop.utils import DbConfig
from junk_shop.capture_repository import BuildParameters
from pony.orm import db_session

DEFAULT_JUNK_SHOP_URL = 'http://junkshop.enk.me/'
DEFAULT_JIRA_URL = 'https://networkoptix.atlassian.net/browse'
DEFAULT_SCM_BROWSER_URL_FORMAT = 'http://enk.me:8082/{repository_name}/revision/{revision}'  # Upsource


def main():
    parser = argparse.ArgumentParser(
        usage='%(prog)s [options]')
    parser.add_argument(
        'db_config', type=DbConfig.from_string,
        metavar='user:password@host',
        help='Capture postgres database credentials')
    parser.add_argument(
        'build_parameters', type=BuildParameters.from_string,
        metavar=BuildParameters.example, help='Build parameters')
    parser.add_argument(
        '--junk-shop-url', default=DEFAULT_JUNK_SHOP_URL,
        help='junk shop URL, default=%s' % DEFAULT_JUNK_SHOP_URL)
    parser.add_argument(
        '--jira-url', default=DEFAULT_JIRA_URL,
        help='JIRA URL, default=%s' % DEFAULT_JIRA_URL)
    parser.add_argument(
        '--scm-browser-url-format', default=DEFAULT_SCM_BROWSER_URL_FORMAT,
        help='SCM browser URL format, default=%s' % DEFAULT_SCM_BROWSER_URL_FORMAT)

    args = parser.parse_args()

    args.db_config.bind(models.db)

    with db_session:
        loader = BuildInfoLoader.from_project_branch_num(
            args.build_parameters.project,
            args.build_parameters.branch,
            args.build_parameters.build_num)
        build_info = loader.load_build_platform_list()
        renderer = TemplateRenderer(args)
        print(renderer.render(
                'build_email.html',
                test_mode=False,
                recipient_list=[],
                **build_info._asdict()))


if __name__ == "__main__":
    main()
