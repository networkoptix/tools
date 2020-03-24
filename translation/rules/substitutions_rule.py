from validation_rule import Levels, ValidationRule


substitutions = ['%1', '%2', '%3', '%4', '%5', '%6', '%7', '%8', '%9']


class SubstitutionsRule(ValidationRule):
    def __str__(self):
        return "Check substitutions"

    def __repr__(self):
        return "<SubstitutionsRule>"

    def level(self):
        return Levels.CRITICAL

    def correct_order(self, source):
        """Check if %2 does not exist without %1"""
        hasPreviuosSubstitution = True
        for symbol in substitutions:
            hasCurrentSubstitution = source.count(symbol) > 0
            if hasCurrentSubstitution and not hasPreviuosSubstitution:
                return False
            hasPreviuosSubstitution = hasCurrentSubstitution
        return True

    def valid_message(self, contextName, message):
        del contextName
        source = ValidationRule.translation_source(message)
        if not self.correct_order(source):
            self.lastErrorText = (u"Invalid substitution order found in:\n\"{0}\""
                                  .format(source))
            return False

        for symbol in substitutions:
            occurences = source.count(symbol)
            for text in ValidationRule.translation_texts(message):
                if not text.count(symbol) == occurences:
                    self.lastErrorText = (
                        u'''Invalid substitution count found in:\n\"{0}\"'''
                        .format(text))
                    return False

        return True
