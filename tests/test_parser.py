import pytest

from lex_graph.parsers.eu import EUXMLParser
from lex_graph.parsers.parser import LegislationParser
from lex_graph.parsers.uk import UKXMLParser
from lex_graph.reference_finders.pattern import (
    EUReferencePatterns,
    PatternReferenceFinder,
    UKReferencePatterns,
)
from lex_graph.types import Legislation


@pytest.fixture
def eu_xml_content():
    with open("tests/test_data/raw/eur-2016-2243-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def uk_xml_content():
    with open("tests/test_data/raw/ukpga-2004-34-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def uk_aep_content():
    with open("tests/test_data/raw/aep-Edw2-7-0-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


def test_create_parser_eu(eu_xml_content):
    parser = LegislationParser.create_parser(eu_xml_content)
    assert isinstance(parser, EUXMLParser)
    assert isinstance(parser.reference_finder, PatternReferenceFinder)
    assert isinstance(parser.reference_finder.patterns, EUReferencePatterns)


def test_create_parser_uk(uk_xml_content):
    parser = LegislationParser.create_parser(uk_xml_content)
    assert isinstance(parser, UKXMLParser)
    assert isinstance(parser.reference_finder, PatternReferenceFinder)
    assert isinstance(parser.reference_finder.patterns, UKReferencePatterns)


def test_parse_eu(eu_xml_content):
    parser = LegislationParser.create_parser(eu_xml_content)
    result = parser.parse(eu_xml_content)
    assert isinstance(result, Legislation)


def test_parse_uk(uk_xml_content):
    parser = LegislationParser.create_parser(uk_xml_content)
    result = parser.parse(uk_xml_content)
    assert isinstance(result, Legislation)


def test_parse_aep(uk_aep_content):
    parser = LegislationParser.create_parser(uk_aep_content)
    result = parser.parse(uk_aep_content)
    assert isinstance(result, Legislation)
