# -*- coding: utf-8 -*-
from validation_rule import Levels, ValidationRule


the = "the"
exceptions = ['I/O', 'Internet', 'App', 'Latest', 'USB']
text_exceptions = ['settings', 'license server']


class TheSubjectRule(ValidationRule):
    def __str__(self):
        return "Check if noun from capital letters goes after \"the\""

    def __repr__(self):
        return "<TheSubjectRule>"

    def level(self):
        return Levels.INFO

    def valid_text(self, text):
        if the not in text.lower():
            return True

        for exclusion in text_exceptions:
            if exclusion in text.lower():
                return True

        awaiting = False
        for word in ValidationRule.words(text):
            if word.lower() == the:
                awaiting = True
                continue
            if not awaiting:
                continue
            if word[0].upper() == word[0] and word not in exceptions:
                self.lastErrorText = u"Capital {0} after \"the\" found in: \"{1}\"".format(
                    word, text)
                return False
            awaiting = False

        return True
