from validation_rule import ValidationRule, Levels

class GlossaryRule(ValidationRule):
    def __str__(self):
        return "Check glossary items"

    def __repr__(self):
        return "<GlossaryRule>"

    def level(self):
        return Levels.CRITICAL

    def valid(self, source, translation):
        apos = '\''
        if not apos in source:
            return True

        for word in (w for w in source.split(' ') if apos in w):
            if word.endswith(apos) or word.endswith('\'s'):
                continue
            self.lastErrorText = u"Invalid contraction found in:\n\"{0}\"".format(source)
            return False
        
        return True        
