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

        for word in (w for w in text.split(' ') if apos in w):
            if word.endswith(apos + 's'):
                continue
            if word.startswith(apos) and word.endswith(apos):
                continue
            self.lastErrorText = u"Invalid contraction \"{0}\" was found in text:\n\"{1}\"".format(
                word, text)
            return False

        return True

    def valid_translations(self, contextName, message):
        del contextName, message
        return True
