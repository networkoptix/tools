from validation_rule import Levels, ValidationRule


exceptions = [
    'nx::vms::event::StringsHelper',
    'QnTimeStrings',
    'HumanReadable',
    'LocalFiles',
    'QnAuditLogDialog',
    'QnCameraAudioTransmitPolicy',
    'QnCameraInputPolicy',
    'QnCameraMotionPolicy',
    'QnCameraOutputPolicy',
    'QnCameraRecordingPolicy',
    'QnLicenseManagerWidget',
    'QnVideowallScreenWidget',
    'QnWorkbenchWearableHandler',
    'CameraLicensePanelWidget',
    'CameraSettingsLicenseWatcher',
    'TileInteractionHandler',
    'LicenseDeactivationDialogs',
    'ContextMenu',
]

template = '%n'


class NumerusFormRule(ValidationRule):
    def __str__(self):
        return "Check numerus forms"

    def __repr__(self):
        return "<NumerusFormRule>"

    def level(self):
        return Levels.CRITICAL

    @staticmethod
    def ignore(contextName, message):
        for exclusion in exceptions:
            if exclusion in contextName:
                return True
        return not ValidationRule.is_numerus(message)

    def valid_source(self, contextName, message):
        if NumerusFormRule.ignore(contextName, message):
            return True

        source = message.find('source')
        if template not in source.text:
            self.lastErrorText = u"Missing template in the numerus source"
            return False

        return True

    def valid_translations(self, contextName, message):
        if not ValidationRule.is_numerus(message):
            return True

        ignoreTemplate = NumerusFormRule.ignore(contextName, message)

        source = message.find('source')
        translation = message.find('translation')
        isFirst = True
        for numerusform in translation.iter('numerusform'):
            if not numerusform.text:
                self.lastErrorText = u"Numerus text is not translated"
                return False

            if not ignoreTemplate and not isFirst and template not in numerusform.text:
                self.lastErrorText = u"""Missing template in numerus form {0}
 found in:\n\"{1}\"""".format(numerusform.text, source.text)
                return False
            isFirst = False

        return True
