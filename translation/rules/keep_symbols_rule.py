from validation_rule import Levels, ValidationRule


symbols = [
    '\n',
    '<b>', '</b>',
    '<i>', '</i>',
    '<s>', '</s>',
    '<u>', '</u>',
    '<font', '</font>',
]


def symbolText(symbol):
    if symbol == '\n':
        return '\\n'
    return symbol


class KeepSymbolsRule(ValidationRule):
    def __str__(self):
        return "Check symbols which must be kept in the translations"

    def __repr__(self):
        return "<KeepSymbolsRule>"

    def level(self):
        return Levels.WARNING

    def valid_message(self, contextName, message):
        del contextName
        source = ValidationRule.translation_source(message)
        for symbol in symbols:
            occurences = source.count(symbol)
            for text in ValidationRule.translation_texts(message):
                if not text.count(symbol) == occurences:
                    self.lastErrorText = (
                        u'''Invalid symbol {0} count found in:\n\"{1}\"\nSource is:\n\"{2}\"'''
                        .format(symbolText(symbol), text, source))
                    return False

        return True
