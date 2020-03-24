import re


class Levels:
    INFO = 0
    WARNING = 1
    CRITICAL = 2


class ValidationRule:
    def __init__(self):
        self.lastErrorText = ""

    def last_error_text(self):
        return self.lastErrorText

    def valid_text(self, text):
        del text
        return True

    def valid_source(self, contextName, message):
        del contextName
        source = message.find('source')
        return self.valid_text(source.text)

    def valid_translations(self, contextName, message):
        del contextName
        return all(self.valid_text(text) for text in ValidationRule.translation_texts(message))

    def valid_message(self, contextName, message):
        return (self.valid_source(contextName, message) and
                self.valid_translations(contextName, message))

    @staticmethod
    def is_numerus(message):
        return message.get('numerus') == 'yes'

    @staticmethod
    def translation_source(message):
        return message.find('source').text

    @staticmethod
    def translation_texts(message):
        isNumerus = ValidationRule.is_numerus(message)
        translation = message.find('translation')
        if isNumerus:
            for numerusform in translation.iter('numerusform'):
                if numerusform.text:
                    yield numerusform.text
        elif translation.text:
            yield translation.text

    @staticmethod
    def words(string):
        return [word for word in re.split('[^a-zA-Z\'/]', string) if word]
