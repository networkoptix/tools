class Levels:
    CRITICAL = "critical"

class ValidationRule:
    def __init__(self):
        self.lastErrorText = ""

    def last_error_text(self):
        return self.lastErrorText

    @staticmethod
    def translation_texts(translation):
        isNumerus = False
        for numerusform in translation.iter('numerusform'):
            isNumerus = True
            if numerusform.text:
                yield numerusform.text
        if translation.text and not isNumerus:
            yield translation.text
