from validation_rule import ValidationRule, Levels

class ContractionsRule(ValidationRule):
    def __str__(self):
        return "Check contractions"

    def __repr__(self):
        return "<ContractionsRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_text(self, text):
        apos = '\''
        if not apos in text:
            return True

        for word in (w for w in text.split(' ') if apos in w):
            self.lastErrorText = u"Invalid contraction found in:\n\"{0}\"".format(text)
            return False
        
        return True

    def valid_translations(self, contextName, message):
        return True
