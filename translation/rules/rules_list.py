#!/bin/python2

from contractions_rule import ContractionsRule
from forbidden_symbols_rule import ForbiddenSymbolsRule
from glossary_rule import GlossaryRule
from leading_trailing_symbols_rule import LeadingTrailingSymbolsRule   

def get_validation_rules():
    yield ForbiddenSymbolsRule()
    yield ContractionsRule()
    yield GlossaryRule()
    yield LeadingTrailingSymbolsRule()

if __name__ == "__main__":
    for rule in get_validation_rules():
        print rule