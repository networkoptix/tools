# -*- coding: utf-8 -*-


from validation_rule import ValidationRule, Levels

class TheSubjectRule(ValidationRule):
    def __str__(self):
        return "Check if noun from capital letters goes after \"the\""

    def __repr__(self):
        return "<TheSubjectRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        the = "the"
        exclusions = ['I/O', 'Internet', 'App']
        text_exclusions = ['settings']
        
        if not the in source.lower():
            return True
        
        for exclusion in text_exclusions:
            if exclusion in source.lower():
                return True
        
        awaiting = False
        for word in ValidationRule.words(source):
            if word.lower() == the:
                awaiting = True
                continue
            if not awaiting:
                continue
            if word[0].upper() == word[0] and not word in exclusions:
                self.lastErrorText = u"Capital {0} after \"the\" found in: \"{1}\"".format(word, source)
                return False
            awaiting = False

        return True
