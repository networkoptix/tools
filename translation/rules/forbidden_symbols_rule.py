# -*- coding: utf-8 -*-

from validation_rule import ValidationRule, Levels

forbidden = ['  ', '&apos;', 'href', '<html', '<br>', '<br/>', '&amp;']

class ForbiddenSymbolsRule(ValidationRule):
    def __str__(self):
        return "Check forbidden symbols"

    def __repr__(self):
        return "<ForbiddenSymbolsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_text(self, text):
        for substring in forbidden:
            if substring in text:
                self.lastErrorText = u"Invalid substring {0} found in:\n\"{1}\"".format(substring, text)
                return False
        return True

