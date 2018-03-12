#!/bin/python2

from contractions_rule import ContractionsRule
from forbidden_symbols_rule import ForbiddenSymbolsRule
from glossary_rule import GlossaryRule
from leading_trailing_symbols_rule import LeadingTrailingSymbolsRule
from at_least_one_alpha_rule import AtLeastOneAlphaRule
from the_subject_rule import TheSubjectRule
from lowercase_rule import LowercaseRule
from numerus_form_rule import NumerusFormRule
from en_us_correction_rule import EnUsCorrectionRule


def get_validation_rules(filename):
    yield ForbiddenSymbolsRule()
    yield ContractionsRule()
    yield GlossaryRule()
    yield LeadingTrailingSymbolsRule()
    yield AtLeastOneAlphaRule()
    yield TheSubjectRule()
    yield LowercaseRule()
    yield NumerusFormRule()
    if 'en_US' in filename:
        yield EnUsCorrectionRule()


if __name__ == "__main__":
    for rule in get_validation_rules():
        print rule
