from validation_rule import ValidationRule, Levels

class AtLeastOneAlphaRule(ValidationRule):
    def __str__(self):
        return "Check if there are at least one alphabet character in the translatable string"

    def __repr__(self):
        return "<AtLeastOneAlphaRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        valid = any(c.isalpha() for c in source)
        if not valid:
            self.lastErrorText = u"No alphabet characters found in:\n\"{0}\"".format(source)
        return valid
