import re

class CommitMessageChecker:
    NX_PROJECT_KEYWORDS = [
        'VMS',
        'UT',
        'CP',
        'CLOUD',
        'PSP',
        'DESIGN',
        'ENV',
        'FR',
        'HNW',
        'LIC',
        'MOBILE',
        'NCD',
        'NXPROD',
        'NXTOOL',
        'STATS',
        'CALC',
        'TEST',
        'VISTA',
        'WEB',
        'WS'
    ]

    def __init__(self):
        self._issue_regex = re.compile(r'\b([A-Z]+)-\d+\b')

    def is_merge_message(self, message):
        return message[:5].lower() == "merge"

    def contains_issue_number(self, message):
        match = self._issue_regex.match(message)
        return match and match.group(1).upper() in self.NX_PROJECT_KEYWORDS

    def is_commit_message_accepted(self, message):
        return not self.is_merge_message(message) and self.contains_issue_number(message)
