import requests
import collections
import json
from datetime import datetime

LIMIT = 10000

AUTHOR_ROLE = 1
REVIEWER_ROLE = 2
WATCHER_ROLE = 3

UNREAD_STATE = 1
READ_STATE = 2
ACCEPTED_STATE = 3
REJECTED_STATE = 4

UNREVIEWED_STATES = (UNREAD_STATE, READ_STATE)
REVIEWED_STATES = (ACCEPTED_STATE, REJECTED_STATE)


class Api(object):
    def __init__(self, url, login, password):
        self.url = url
        self.api_url = url + '/~rpc/'
        self.auth = (login, password)

    def get(self, method, **kwargs):
        response = requests.post(
            self.api_url + '/' + method,
            auth=self.auth,
            data=json.dumps(kwargs))
        if response.status_code / 100 != 2:
            raise ValueError('Unable to get {} -- {}'.format(response.url, response.status_code))

        return json.loads(response.text)['result']

    def reviews(self, query):
        result = self.get('getReviews', query=query, limit=LIMIT)
        if not result or 'reviews' not in result:
            raise KeyError('Query "{}" returned no reviews: {}'.format(query, str(result)))
        return result['reviews']

    def user(self, id, field=None):
        infos = self.get('getUserInfo', ids=[id])['infos']
        if not infos:
            raise KeyError('Unknown user: {}'.format(id))

        return infos[0][field] if field else infos[0]

    def todo(self):
        Review = collections.namedtuple(
            'Review',
            ['id', 'project_id', 'authors', 'reviewers', 'age'])
        result = []
        for review in self.reviews('state: open'):
            reviewId = review['reviewId']['reviewId']
            projectId = review['reviewId']['projectId']

            def users(search):
                return [user['userId'] for user in review.get('participants', []) if search(user)]

            result.append(Review(
                reviewId,
                projectId,
                users(lambda u: u['role'] == AUTHOR_ROLE),
                users(lambda u: u['role'] == REVIEWER_ROLE and u['state'] in UNREVIEWED_STATES),
                datetime.now() - datetime.fromtimestamp(review['updatedAt'] / 1000),
            ))

        return result
