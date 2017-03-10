import re

class Levels:
    CRITICAL = "critical"

class ValidationRule:
    def __init__(self):
        self.lastErrorText = ""

    def last_error_text(self):
        return self.lastErrorText

    def valid_text(self, text):
        return True
        
    def valid_source(self, source):
        return self.valid_text(source)
        
    def valid_translations(self, source, translation):
        return all(self.valid_text(text) for text in ValidationRule.translation_texts(translation))
        
    @staticmethod
    def translation_texts(translation):
        isNumerus = False
        for numerusform in translation.iter('numerusform'):
            isNumerus = True
            if numerusform.text:
                yield numerusform.text
        if translation.text and not isNumerus:
            yield translation.text

    @staticmethod
    def words(string):        
        return [word for word in re.split('[^a-zA-Z\'/]', string) if word]
