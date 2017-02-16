from validation_rule import ValidationRule, Levels

class LeadingTrailingSymbolsRule(ValidationRule):
    def __str__(self):
        return "Check leading and trailing symbols"

    def __repr__(self):
        return "<LeadingTrailingSymbolsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        leading = [' ', '<', '&lt;']
        for substring in leading:
            if source.startswith(substring):
                self.lastErrorText = u"Invalid leading substring {0} found in source:\n\"{1}\"".format(substring, source)
                return False
            for text in ValidationRule.translation_texts(translation):
                if text.startswith(substring):
                    self.lastErrorText = u"Invalid leading substring {0} found in translation:\n\"{1}\"".format(substring, text)
                    return False

        #colons, dots will possibly be here
        trailing = [' ']
        for substring in trailing:
            if source.endswith(substring):
                self.lastErrorText = u"Invalid trailing substring {0} found in source:\n\"{1}\"".format(substring, source)
                return False
            for text in ValidationRule.translation_texts(translation):
                if text.endswith(substring):
                    self.lastErrorText = u"Invalid trailing substring {0} found in translation:\n\"{1}\"".format(substring, text)
                    return False

        return True
