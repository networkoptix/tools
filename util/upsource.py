#!/usr/bin/env python

import collections
import json
import requests
from datetime import datetime
from pprint import pprint

AUTHOR_ROLE = 1
REVIEWER_ROLE = 2
WATCHER_ROLE = 3

UNREAD_STATE = 1
READ_STATE = 2
ACCEPTED_STATE = 3
REJECTED_STATE = 4

UNREVIEWED_STATES = (UNREAD_STATE, READ_STATE)
REVIEWED_STATES = (ACCEPTED_STATE, REJECTED_STATE)
    
LIMIT = 10000


class Api(object):
    def __init__(self, url, login, password):
        self.url = url + '/~rpc/'
        self.auth = (login, password)
           
    def get(self, method, **kwargs):
        response = requests.post(self.url + '/' + method, auth=self.auth, data=json.dumps(kwargs))
        if response.status_code / 100 != 2:
            raise ValueError('Unable to get {} -- {}'.format(response.url, response.status_code))
        
        return json.loads(response.text)['result']
        
    def reviews(self, query):
        return self.get('getReviews', query=query, limit=LIMIT)['reviews']
         
    def user(self, id, field=None):
        infos = self.get('getUserInfo', ids=[id])['infos']
        if not infos:
            raise KeyError('Unknown user: {}'.format(id))
            
        return infos[0][field] if field else infos[0]
        
    def todo(self):
        Review = collections.namedtuple('Review', ['id', 'authors', 'reviewers', 'age'])
        result = []
        for review in self.reviews('state: open'):
            reviewId = review['reviewId']['reviewId']
            
            def users(search):
                return [user['userId'] for user in review.get('participants', []) if search(user)]
                        
            result.append(Review(
                reviewId, 
                users(lambda u: u['role'] == AUTHOR_ROLE),
                users(lambda u: u['role'] == REVIEWER_ROLE and u['state'] in UNREVIEWED_STATES),
                datetime.now() - datetime.fromtimestamp(review['updatedAt'] / 1000),
            ))
            
        return result

        
def print_todo(api, user_grep='', flags=''):
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
            
    def print_review_list(title, reviews):
        if reviews:
            reviews.sort(key=lambda r: -r.age)
            print('  {} ({}): {}'.format(title, len(reviews), ', '.join([
                '{} ({} days)'.format(r.id, r.age.days) for r in reviews])))
            print('')
            
    total_count = 0
    for user_id, todo in by_users.items():
        name = api.user(user_id, 'name')
        if user_grep in name:        
            count = len(todo.to_fix) + len(todo.to_review)
            total_count += count
            print('{} ({})'.format(name, count))
            if 'users-only' not in flags:
                print('')
                print_review_list('Fix or close', todo.to_fix)
                print_review_list('Review or quit', todo.to_review)
    
    print('')
    print('Total reviews to cleanup: {}'.format(total_count))

        
def print_reviews(api, *query):
    pprint(api.get('getReviews', query=' '.join(query), limit=LIMIT)['reviews'])
        

def print_users(api, *ids):
    for id in ids:
        pprint(api.user(id))

        
if __name__ == '__main__':
    import argparse
    import sys
    
    parser = argparse.ArgumentParser()
    parser.add_argument('action', nargs='?', default='todo', help='todo, reviews, users')
    parser.add_argument('options', nargs='*', default=[])
    parser.add_argument('-U', '--url', default='http://enk.me:8082')
    parser.add_argument('-u', '--user', default='')
    parser.add_argument('-p', '--password', default='')
    
    arguments = parser.parse_args()
    api = Api(arguments.url, arguments.user, arguments.password)
    action = globals().get('print_' + arguments.action)
    if not action:
        print('Unknown action: {}'.format(arguments.action))
        exit(1)
        
    try:
        action(api, *arguments.options)
    except Exception as error:
        print(str(error))
        exit(1)
