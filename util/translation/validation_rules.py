#!/bin/python2

class Levels:
    CRITICAL = "critical"

class ForbiddenSymbolsRule:
    def __init__(self):
        self.lastErrorText = ""

    def __str__(self):
        return "Check forbidden symbols"

    def __repr__(self):
        return "<ForbiddenSymbolsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        invalid = ['  ', '\'', '&apos;', 'href', '<html', '<br>', '<br/>']
        for substring in invalid:
            if substring in source:
                self.lastErrorText = u"Invalid substring {0} found in:\n\"{1}\"".format(substring, source)
                return False
                
        return True
        
    def last_error_text(self):
        return self.lastErrorText

def get_validation_rules():
    yield ForbiddenSymbolsRule()

if __name__ == "__main__":
    for rule in get_validation_rules():
        print rule