from validation_rule import Levels, ValidationRule


exceptions = ['Language Name']


class EnUsCorrectionRule(ValidationRule):
    def __str__(self):
        return "Check en-US corrections from previous versions"

    def __repr__(self):
        return "<EnUsCorrectionRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_message(self, contextName, message):
        valid = (ValidationRule.is_numerus(message) or
                 ValidationRule.translation_source(message) in exceptions or
                 len(list(ValidationRule.translation_texts(message))) == 0)
        if not valid:
            self.lastErrorText = u"En-US correction in:\n\"{0}\"".format(
                ValidationRule.translation_source(message))
        return valid

    def valid_translations(self, contextName, message):
        return True
