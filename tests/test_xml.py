from datetime import date

import pytest
from bs4 import BeautifulSoup

from lex_graph.parsers.parser import LegislationParser
from lex_graph.types import GeographicalExtent


@pytest.fixture
def sample_xml():
    with open("tests/test_data/raw/housing_act_sample.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def parser(sample_xml):
    return LegislationParser.create_parser(sample_xml)


def test_extract_text(parser):
    xml = "<root><element>Some text &amp; more text</element></root>"
    soup = BeautifulSoup(xml, "xml")
    element = soup.find("element")
    assert parser._extract_text(element) == "Some text & more text"


def test_extract_date(parser):
    xml = "<root><element>2023-10-01</element></root>"
    soup = BeautifulSoup(xml, "xml")
    element = soup.find("element")
    assert parser._extract_date(element) == date(2023, 10, 1)


def test_extract_value(parser):
    xml = '<root><element Value="Some value"/></root>'
    soup = BeautifulSoup(xml, "xml")
    element = soup.find("element")
    assert parser._extract_value(element) == "Some value"


def test_clean_text(parser):
    text = "  Some   text &amp; more text  "
    assert parser._clean_text(text) == "Some text & more text"


def test_restrict_extent_to_string(parser):
    assert parser._restrict_extent_to_string("E+W+S+N.I.") == "United Kingdom"
    assert parser._restrict_extent_to_string("E+W+S+NI") == "United Kingdom"
    assert parser._restrict_extent_to_string("E+W") == "England, Wales"
    assert parser._restrict_extent_to_string("") == ""


def test_map_extent(parser):
    assert parser.map_extent("E") == [GeographicalExtent.E]
    assert parser.map_extent("E+W") == [GeographicalExtent.E, GeographicalExtent.W]
    assert parser.map_extent("E+W+S+N.I") == [GeographicalExtent.UK]
    assert parser.map_extent("E+W+S+NI") == [GeographicalExtent.UK]
    assert parser.map_extent(None) == [GeographicalExtent.NONE]


def test_parse(parser, sample_xml):
    legislation = parser.parse(sample_xml)

    # Top level attributes
    assert legislation.id == "http://www.legislation.gov.uk/id/ukpga/2004/34"
    assert legislation.uri == "http://www.legislation.gov.uk/ukpga/2004/34"
    assert legislation.title == "Housing Act 2004"
    assert (
        legislation.description
        == "An Act to make provision about housing conditions; to regulate houses in multiple occupation and certain other residential accommodation; to make provision for home information packs in connection with the sale of residential properties; to make provision about secure tenants and the right to buy; to make provision about mobile homes and the."
    )
    assert legislation.valid_date == date(2022, 4, 28)
    assert legislation.modified_date == date(2022, 5, 25)
    assert legislation.publisher == "Statute Law Database"
    assert legislation.category == "primary"
    assert legislation.type == "UnitedKingdomPublicGeneralAct"
    assert legislation.status == "revised"
    assert legislation.enactment_date == date(2004, 11, 18)
    assert legislation.extent == [GeographicalExtent.UK]

    # Provisions
    assert legislation.number_of_provisions == 647

    assert len(legislation.sections) == 1
    assert (
        legislation.sections[0].id
        == "http://www.legislation.gov.uk/id/ukpga/2004/34/section/1"
    )
    assert (
        legislation.sections[0].text
        == "New system for assessing housing conditions and enforcing housing standards"
    )
    assert (
        legislation.sections[0].text
        == "New system for assessing housing conditions and enforcing housing standards"
    )

    assert len(legislation.sections[0].paragraphs) == 3
    assert (
        legislation.sections[0].paragraphs[0].text
        == "This Part provides— a for a new system of assessing the condition of residential premises, and b for that system to be used in the enforcement of housing standards in relation to such premises."
    )
    assert legislation.sections[0].paragraphs[0].number == "1"
    assert (
        legislation.sections[0].paragraphs[1].text
        == "The new system— a operates by reference to the existence of category 1 or category 2 hazards on residential premises (see section 2), and b replaces the existing system based on the test of fitness for human habitation contained in section 604 of the Housing Act 1985 (c. 68)."
    )
    assert legislation.sections[0].paragraphs[1].number == "2"

    assert len(legislation.schedules) == 1
    assert (
        legislation.schedules[0].id
        == "http://www.legislation.gov.uk/id/ukpga/2004/34/schedule/1"
    )
    assert (
        legislation.schedules[0].text
        == "Procedure and appeals relating to improvement notices"
    )
    assert legislation.schedules[0].commentary_refs == ["c2051523"]

    assert len(legislation.schedules[0].paragraphs) == 1
    assert (
        legislation.schedules[0].paragraphs[0].id
        == "http://www.legislation.gov.uk/id/ukpga/2004/34/schedule/1/paragraph/1"
    )
    assert legislation.schedules[0].paragraphs[0].number == "1"
    assert (
        legislation.schedules[0].paragraphs[0].text
        == "This paragraph applies where the specified premises in the case of an improvement notice are— a a dwelling which is licensed under Part 3 of this Act, or"
    )
    assert legislation.schedules[0].paragraphs[0].commentary_refs == ["c2051523"]

    assert len(legislation.commentaries) == 2
    assert "c2050708" in legislation.commentaries
    assert "c2051523" in legislation.commentaries
    assert legislation.commentaries["c2051523"].id == "c2051523"
    assert legislation.commentaries["c2051523"].type == "I"
    assert len(legislation.commentaries["c2051523"].citations) == 6
