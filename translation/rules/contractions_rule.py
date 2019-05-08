from validation_rule import Levels, ValidationRule


class ContractionsRule(ValidationRule):
    def __str__(self):
        return "Check contractions"

    def __repr__(self):
        return "<ContractionsRule>"

    def level(self):
        return Levels.WARNING

    def valid_text(self, text):
        apos = '\''
        if apos not in text:
            return True

        for word in (w for w in text.split(' ') if apos in w and not w.endswith(apos + 's')):
            self.lastErrorText = u"Invalid contraction found in:\n\"{0}\"".format(text)
            return False

        return True

    def valid_translations(self, contextName, message):
        return True
