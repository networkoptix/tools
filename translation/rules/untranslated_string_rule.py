from validation_rule import Levels, ValidationRule


class UntranslatedStringRule(ValidationRule):
    def __str__(self):
        return "Check strings which marked as translated but actually not"

    def __repr__(self):
        return "<UntranslatedStringRule>"

    def level(self):
        return Levels.INFO

    def valid_message(self, contextName, message):
        del contextName
        source = ValidationRule.translation_source(message)
        for text in ValidationRule.translation_texts(message):
            if text == source:
                self.lastErrorText = (
                    u'''String looks like untranslated:\n\"{0}\"'''
                    .format(text))
                return False

        return True
