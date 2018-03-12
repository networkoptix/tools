from validation_rule import ValidationRule, Levels

leading = [' ', '<', '&lt;']
trailing = [' '] #colons, dots will possibly be here


class LeadingTrailingSymbolsRule(ValidationRule):
    def __str__(self):
        return "Check leading and trailing symbols and other forbidden symbols"

    def __repr__(self):
        return "<LeadingTrailingSymbolsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_text(self, text):
        for substring in leading:
            if text.startswith(substring):
                self.lastErrorText = u"Invalid leading substring {0} found in text:\n\"{1}\"".format(substring, text)
                return False

        for substring in trailing:
            if text.endswith(substring):
                self.lastErrorText = u"Invalid trailing substring {0} found in text:\n\"{1}\"".format(substring, text)
                return False

        return True
