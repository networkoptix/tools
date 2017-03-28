from validation_rule import ValidationRule, Levels

case_sensitive = [
    'URL', 'Hi-Res', 'Custom-Res',
    'ID', 'PTZ',
#    'License Key',
#    'Hardware Id',
    'Email', 'the Internet',
    'System', "Systems",
    'B', 'KB', 'MB', 'GB', 'TB'
    ]

invalid_terms = {
    'low-res': 'Lo-Res',
    'qnt': 'Qty',
    'e-mail': 'Email',
    'media server': 'server'
    }

exclusions = ['system tray', 'system administrator', '<b>']
            
class GlossaryRule(ValidationRule):
    def __str__(self):
        return "Check glossary items"

    def __repr__(self):
        return "<GlossaryRule>"

    def level(self):
        return Levels.CRITICAL

    def valid_text(self, text):
        for exclusion in exclusions:
            if exclusion in text:
                return True

        plain_text = text.lower()
        for term in case_sensitive:
            idx = plain_text.find(term.lower())
            if idx < 0:
                continue
            substr = text[idx:idx+len(term)]
            if idx > 0 and text[idx - 1].isalpha():
                continue

            next_idx = idx + len(term)
            if next_idx < len(text) and text[next_idx].isalpha():
                continue

            if substr != term:
                self.lastErrorText = u"Invalid term {0} instead of {1} found in: \"{2}\"".format(substr, term, text)
                return False

        for term, fix in invalid_terms.items():
            if term.lower() in plain_text:
                self.lastErrorText = u"Invalid term {0} instead of {1} found in: \"{2}\"".format(term, fix, text)
                return False

        return True