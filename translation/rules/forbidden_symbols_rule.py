# -*- coding: utf-8 -*-
from validation_rule import Levels, ValidationRule


forbidden = [
    '  ',  # Double space.
    '&apos;',
    'href',
    '\t',
    '&amp;',
    'Ctrl+', 'Shift+', 'Alt+',
    '<html'
]


def symbolText(symbol):
    if symbol == '\t':
        return '\\t'
    if symbol == '\n':
        return '\\n'
    if symbol == '  ':
        return '<Double space>'
    return symbol


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
                self.lastErrorText = (u"Invalid substring {0} found in:\n\"{1}\""
                                      .format(symbolText(substring), text))
                return False
        return True
