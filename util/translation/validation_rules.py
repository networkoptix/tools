#!/bin/python2

class Levels:
    CRITICAL = "critical"

class ValidationRule:
    def __init__(self):
        self.lastErrorText = ""

    def last_error_text(self):
        return self.lastErrorText

class ForbiddenSymbolsRule(ValidationRule):
    def __str__(self):
        return "Check forbidden symbols"

    def __repr__(self):
        return "<ForbiddenSymbolsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        forbidden = ['  ', '&apos;', 'href', '<html', '<br>', '<br/>']
        for substring in forbidden:
            if substring in source:
                self.lastErrorText = u"Invalid substring {0} found in:\n\"{1}\"".format(substring, source)
                return False

        return True

class ContractionsRule(ValidationRule):
    def __str__(self):
        return "Check contractions"

    def __repr__(self):
        return "<ContractionsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        apos = '\''
        if not apos in source:
            return True

        for word in (w for w in source.split(' ') if apos in w):
            if word.endswith(apos) or word.endswith('\'s'):
                continue
            self.lastErrorText = u"Invalid contraction found in:\n\"{0}\"".format(source)
            return False
        
        return True


def get_validation_rules():
    yield ForbiddenSymbolsRule()
    yield ContractionsRule()

if __name__ == "__main__":
    for rule in get_validation_rules():
        print rule