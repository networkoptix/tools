# -*- coding: utf-8 -*-
from validation_rule import Levels, ValidationRule


words = ['Email']
exceptions = ['Email Settings']


class LowercaseRule(ValidationRule):
    def __str__(self):
        return "Check if given nouns are not uppercases when it is not needed."

    def __repr__(self):
        return "<LowercaseRule>"

    def level(self):
        return Levels.INFO

    def valid_text(self, text):
        for msg in exceptions:
            if msg in text:
                return True

        source_words = ValidationRule.words(text)[1:]

        for word in words:
            if word not in source_words:
                continue

            self.lastErrorText = u"Capitalized {0} found in: \"{1}\"".format(word, text)
            return False

        return True
