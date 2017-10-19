from validation_rule import ValidationRule, Levels

exclusions = [
    'QnStreamQualityStrings'
    ]

class AtLeastOneAlphaRule(ValidationRule):
    def __str__(self):
        return "Check if there are at least one alphabet character in the translatable string"

    def __repr__(self):
        return "<AtLeastOneAlphaRule>"

    def level(self):
        return Levels.CRITICAL

    @staticmethod
    def ignore(contextName, message):
        for exclusion in exclusions:
            if exclusion in contextName:
                return True
        return False

    def valid_text(self, text):
        valid = any(c.isalpha() for c in text)
        if not valid:
            self.lastErrorText = u"No alphabet characters found in:\n\"{0}\"".format(text)
        return valid

    def valid_translations(self, contextName, message):
        if AtLeastOneAlphaRule.ignore(contextName, message):
            return True
        return ValidationRule.valid_translations(self, contextName, message)