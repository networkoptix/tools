from validation_rule import ValidationRule, Levels

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
