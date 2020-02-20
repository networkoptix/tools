import os
import re
import xml.etree.ElementTree as ET


def migrate_xml(source_root, target_root):
    filter = "./context[name='HumanReadable']"
    source_context = source_root.find(filter)
    source_strings = {}
    for message in source_context.iter('message'):
        source_string = message.find('source').text
        translation = message.find('translation')
        if message.get('numerus') == 'yes':
            numerus_forms = []
            for numerusform in translation.iter('numerusform'):
                numerus_forms.append(numerusform.text)
            source_strings[source_string] = numerus_forms
        else:
            source_strings[source_string] = translation.text

    target_context = target_root.find(filter)
    for message in target_context.iter('message'):
        source_string = message.find('source').text
        translation = message.find('translation')
        source_translations = source_strings[source_string]
        if not source_translations:
            continue

        if message.get('numerus') == 'yes':
            assert(type(source_translations) is list)
            index = 0
            for numerusform in translation.iter('numerusform'):
                numerusform.text = source_translations[index]
                index += 1
        else:
            assert(type(source_translations) is not list)
            translation.text = source_translations


def migrate_language(language):
    source_file = 'client_core_' + language + '.ts'
    if not os.path.isfile(source_file):
        raise FileNotFoundError(source_file)
    source_tree = ET.parse(source_file)
    source_root = source_tree.getroot()

    target_file = 'common_' + language + '.ts'
    if not os.path.isfile(target_file):
        raise FileNotFoundError(target_file)
    target_tree = ET.parse(target_file)
    target_root = target_tree.getroot()
    migrate_xml(source_root, target_root)
    target_tree.write(target_file, encoding="utf-8", xml_declaration=True)


def main():
    for f in os.listdir(os.getcwd()):
        match = re.search('common_(.+)\\.ts', f)
        if match:
            language = match.group(1)
            migrate_language(language)


if __name__ == "__main__":
    main()
