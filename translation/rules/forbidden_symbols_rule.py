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


SYMBOL_TEXT = {
    '\t': '\\t',
    '\n': '\\n',
    '  ': '<Double space>',
}


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
                                      .format(SYMBOL_TEXT.get(substring, substring), text))
                return False
        return True
