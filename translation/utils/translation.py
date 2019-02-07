import xml.etree.ElementTree as ElementTree


class Message():
    def __init__(self, message):
        self.message = message
        self.source = message.find('source').text
        self.translation = message.find('translation')
        self.type = self.translation.get('type')
        self.is_numerus = message.get('numerus') == 'yes'
        self.text = None
        self.texts = None
        if self.is_numerus:
            self.texts = []
            for numerusform in self.translation.iter('numerusform'):
                self.texts.append(numerusform.text)
        else:
            self.text = self.translation.text

    def is_valid(self):
        return self.source is not None and self.type != 'obsolete'

    def is_complete(self):
        return self.type != 'unfinished'

    def update_from(self, other):
        assert(self.is_numerus == other.is_numerus)

        if self.is_numerus:
            self.texts = other.texts
            index = 0
            for numerusform in self.translation.iter('numerusform'):
                numerusform.text = self.texts[index]
                index += 1
        else:
            self.text = other.text
            self.translation.text = self.text
        self.type = None
        self.translation.attrib.pop('type', None)


class Context():
    def __init__(self, context):
        self.context = context
        self.name = context.find('name').text
        self.messages = {}
        for message in [Message(x) for x in context.iter('message')]:
            if message.is_valid():
                self.messages[message.source] = message

    def is_valid(self):
        return self.name is not None and len(self.messages) > 0


class File():
    def __init__(self, path):
        self.path = path
        self.tree = ElementTree.parse(path)
        self.root = self.tree.getroot()
        self.contexts = {}
        for context in [Context(x) for x in self.root]:
            if context.is_valid():
                self.contexts[context.name] = context

    def flush(self):
        self.tree.write(self.path, encoding="utf-8", xml_declaration=True)
