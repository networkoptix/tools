from validation_rule import Levels, ValidationRule


class AtLeastOneAlphaRule(ValidationRule):
    def __str__(self):
        return "Check if there are at least one alphabet character in the translatable string"

    def __repr__(self):
        return "<AtLeastOneAlphaRule>"

    def level(self):
        return Levels.WARNING

    def valid_text(self, text):
        valid = any(c.isalpha() for c in text)
        if not valid:
            self.lastErrorText = u"No alphabet characters found in:\n\"{0}\"".format(text)
        return valid
