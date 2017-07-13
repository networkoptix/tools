# -*- coding: utf-8 -*-

from validation_rule import ValidationRule, Levels

the = "the"
exclusions = ['I/O', 'Internet', 'App', 'Latest']
text_exclusions = ['settings', 'license server']

class TheSubjectRule(ValidationRule):
    def __str__(self):
        return "Check if noun from capital letters goes after \"the\""

    def __repr__(self):
        return "<TheSubjectRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_text(self, text):     
        if not the in text.lower():
            return True
        
        for exclusion in text_exclusions:
            if exclusion in text.lower():
                return True
        
        awaiting = False
        for word in ValidationRule.words(text):
            if word.lower() == the:
                awaiting = True
                continue
            if not awaiting:
                continue
            if word[0].upper() == word[0] and not word in exclusions:
                self.lastErrorText = u"Capital {0} after \"the\" found in: \"{1}\"".format(word, text)
                return False
            awaiting = False

        return True
