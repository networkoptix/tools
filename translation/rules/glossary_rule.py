from validation_rule import ValidationRule, Levels

class GlossaryRule(ValidationRule):
    def __str__(self):
        return "Check glossary items"

    def __repr__(self):
        return "<GlossaryRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_text(self, text):
        case_sensitive = [
            'URL', 'Hi-Res', 'Custom-Res', 'Email', 'ID', 'PTZ',
            'B', 'KB', 'MB', 'GB', 'TB'
            ]
        invalid_terms = {
            'low-res': 'Lo-Res',
            'qnt': 'Qty',
            'e-mail': 'Email'
        }
        
        for word in text.split(' '):
            for term in case_sensitive:
                if word.lower() == term.lower() and word != term:
                    self.lastErrorText = u"Invalid term {0} instead of {1} found in:\n\"{2}\"".format(word, term, text)
                    return False
                    
            for term, fix in invalid_terms.items():
                if word.lower() == term.lower():
                    self.lastErrorText = u"Invalid term {0} instead of {1} found in:\n\"{2}\"".format(word, fix, text)
                    return False     

        return True


    def valid(self, source, translation):
        if not self.valid_text(source):
            return False

        for text in ValidationRule.translation_texts(translation):
            if not self.valid_text(text):
                return False

        return True
