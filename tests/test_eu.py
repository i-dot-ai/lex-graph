import pytest
from bs4 import BeautifulSoup

from lex_graph.parsers.eu import EUXMLParser
from lex_graph.reference_finders.pattern import (
    EUReferencePatterns,
    PatternReferenceFinder,
)
from lex_graph.types import Commentary, Schedule, Section


@pytest.fixture
def parser():
    return EUXMLParser(PatternReferenceFinder(EUReferencePatterns()))


@pytest.fixture
def sample_xml():
    with open("tests/test_data/raw/eur-2016-2243-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def second_sample_xml():
    with open("tests/test_data/raw/eudn-2007-257-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def parsed_sample_content(parser, sample_xml):
    xml_soup = BeautifulSoup(sample_xml, "xml")
    return parser.parse_content(xml_soup)


@pytest.fixture
def parsed_second_sample_content(parser, second_sample_xml):
    xml_soup = BeautifulSoup(second_sample_xml, "xml")
    return parser.parse_content(xml_soup)


def test_parse_content(parsed_sample_content):
    sections, schedules, commentaries = parsed_sample_content
    assert True  # Just test that it runs


def test_parse_content_second_file(parsed_second_sample_content):
    sections, schedules, commentaries = parsed_second_sample_content
    assert True  # Just test that it runs


def test_parse_sections(parsed_sample_content):
    sections, _, _ = parsed_sample_content

    assert len(sections) == 2

    # Check section 1
    section = sections["http://www.legislation.gov.uk/id/eur/2016/2243/article/1"]
    assert isinstance(section, Section)
    assert section.id == "http://www.legislation.gov.uk/id/eur/2016/2243/article/1"
    assert (
        section.text
        == "Annex I to Regulation (EC) No 341/2007 is replaced by the text in the Annex to this Regulation."
    )
    assert len(section.paragraphs) == 0

    # Check section 2
    section = sections["http://www.legislation.gov.uk/id/eur/2016/2243/article/2"]
    assert isinstance(section, Section)
    assert section.id == "http://www.legislation.gov.uk/id/eur/2016/2243/article/2"
    assert (
        section.text
        == "This Regulation shall enter into force on the third day following that of its publication in the Official Journal of the European Union."
    )
    assert len(section.paragraphs) == 0


def test_parse_sections_second_file(parsed_second_sample_content):
    sections, _, _ = parsed_second_sample_content

    assert len(sections) == 2

    # Check section 1
    section = sections["http://www.legislation.gov.uk/id/eudn/2007/257/article/1"]
    assert isinstance(section, Section)
    assert section.id == "http://www.legislation.gov.uk/id/eudn/2007/257/article/1"
    assert (
        section.text
        == "State aid amounting to PLN 66,377 million which has been granted to or is planned for HSW and some of which Poland has already partially or fully implemented in contravention of Article 88(3) of the EC Treaty and some of which Poland has not yet implemented is compatible with the common market."
    )
    assert len(section.paragraphs) == 0

    # Check section 2
    section = sections["http://www.legislation.gov.uk/id/eudn/2007/257/article/2"]
    assert isinstance(section, Section)
    assert section.id == "http://www.legislation.gov.uk/id/eudn/2007/257/article/2"
    assert section.text == "This Decision is addressed to the Republic of Poland."
    assert len(section.paragraphs) == 0


def test_parse_schedules(parsed_sample_content):
    _, schedules, _ = parsed_sample_content

    assert len(schedules) == 1

    schedule = schedules["http://www.legislation.gov.uk/id/eur/2016/2243/annex"]
    assert isinstance(schedule, Schedule)
    assert schedule.id == "http://www.legislation.gov.uk/id/eur/2016/2243/annex"
    assert (
        schedule.text
        == "Tariff quotas opened pursuant to Decisions 2001/404/EC, 2006/398/EC, 2014/116/EU and (EU) 2016/243 for imports of garlic falling within CN code 0703 20 00"
    )
    assert len(schedule.paragraphs) == 1
    assert schedule.paragraphs[0].text.startswith(
        "ANNEX I Tariff quotas opened pursuant to Decisions 2001/404/EC, 2006/398/EC, 2014/116/EU and (EU) 2016/243 for imports of garlic falling within CN code 0703 20 00"
    )


def test_parse_schedules_second_file(parsed_second_sample_content):
    _, schedules, _ = parsed_second_sample_content

    assert len(schedules) == 0  # No schedules in this document


@pytest.mark.xfail(reason="EU commentaries parsing not implemented yet")
def test_parse_commentaries(parsed_sample_content):
    _, _, commentaries = parsed_sample_content

    assert len(commentaries) == 4

    commentary = commentaries["f00001"]
    assert isinstance(commentary, Commentary)
    assert commentary.id == "f00001"
    assert commentary.text == ""
    assert len(commentary.citations) == 0


@pytest.mark.xfail(reason="EU commentaries parsing not implemented yet")
def test_parse_commentaries_second_file(parsed_second_sample_content):
    _, _, commentaries = parsed_second_sample_content

    assert len(commentaries) == 0  # No commentaries in this document


@pytest.mark.xfail(reason="Stats regarding number of provisions are unclear")
def test_number_of_provisions(parsed_sample_content, sample_xml):
    """Test the number of parsed provisions matches the provision stats attribute."""
    sections, schedules, commentaries = parsed_sample_content
    xml_soup = BeautifulSoup(sample_xml, "xml")

    number_of_provisions = int(xml_soup.find("ukm:TotalParagraphs")["Value"])
    number_sections = int(xml_soup.find("ukm:BodyParagraphs")["Value"])
    number_schedule = int(xml_soup.find("ukm:ScheduleParagraphs")["Value"])

    total_provisions = len(sections) + len(schedules)

    assert number_sections == len(sections)
    assert number_schedule == len(schedules)
    assert total_provisions == number_of_provisions


@pytest.mark.xfail(reason="Stats regarding number of provisions are unclear")
def test_number_of_provisions_second_file(
    parsed_second_sample_content, second_sample_xml
):
    """Test the number of parsed provisions matches the provision stats attribute."""
    sections, schedules, commentaries = parsed_second_sample_content
    xml_soup = BeautifulSoup(second_sample_xml, "xml")

    number_of_provisions = int(xml_soup.find("ukm:TotalParagraphs")["Value"])
    number_sections = int(xml_soup.find("ukm:BodyParagraphs")["Value"])
    number_schedule = int(xml_soup.find("ukm:ScheduleParagraphs")["Value"])

    total_provisions = len(sections) + len(schedules)

    assert number_sections == len(sections)
    assert number_schedule == len(schedules)
    assert total_provisions == number_of_provisions
