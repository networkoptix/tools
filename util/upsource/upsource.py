#!/usr/bin/env python

import collections
import api
import printers
from pprint import pprint


def print_todo(api, format, user_grep='', flags=''):

    Todo = collections.namedtuple('Todo', ['to_fix', 'to_review'])
    by_users = {}

    def todo(user_id):
        return by_users.setdefault(user_id, Todo([], []))

    for review in api.todo():
        for user in review.reviewers:
            todo(user).to_review.append(review)
        if not review.reviewers:
            for user in review.authors:
                todo(user).to_fix.append(review)

    User = collections.namedtuple('User', ['id', 'name', 'todo'])
    users = []
    for user_id, todo in by_users.items():
        user = User(user_id, api.user(user_id, 'name'), todo)
        users.append(user)
    users.sort(key=lambda x: x.name)

    printer = printers.HtmlPrinter(api.url) if format == 'html' else printers.TxtPrinter()

    with printer:
        total_count = 0
        for user in users:
            if user_grep in user.name:
                count = len(user.todo.to_fix) + len(user.todo.to_review)
                total_count += count
                printer.user_title(user.id, user.name, count)
                if 'users-only' not in flags:
                    printer.review_list('Fix or close', user.todo.to_fix)
                    printer.review_list('Review or quit', user.todo.to_review)


def print_reviews(api, format, *query):
    pprint(api.get('getReviews', query=' '.join(query), limit=api.LIMIT)['reviews'])


def print_users(api, format, *ids):
    for id in ids:
        pprint(api.user(id))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('options', nargs='*', default=[])
    parser.add_argument('-a', '--action', choices=['todo, reviews, users'], default='todo')
    parser.add_argument('-U', '--url', default='http://enk.me:8082')
    parser.add_argument('-u', '--user', default='')
    parser.add_argument('-p', '--password', default='')
    parser.add_argument('-f', '--format', choices=['txt', 'html'], default='txt')

    arguments = parser.parse_args()
    api = api.Api(arguments.url, arguments.user, arguments.password)
    action = globals().get('print_' + arguments.action)
    if not action:
        print('Unknown action: {}'.format(arguments.action))
        exit(1)

    try:
        action(api, arguments.format, *arguments.options)
    except Exception as error:
        print(str(error))
        exit(1)
