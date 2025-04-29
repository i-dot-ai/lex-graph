import pytest
from bs4 import BeautifulSoup

from lex_graph.parsers.uk import UKXMLParser
from lex_graph.reference_finders.pattern import (
    PatternReferenceFinder,
    UKReferencePatterns,
)
from lex_graph.types import GeographicalExtent


@pytest.fixture(scope="module")
def xml_parser():
    parser = UKXMLParser(PatternReferenceFinder(UKReferencePatterns()))
    return parser


@pytest.fixture
def sample_xml():
    with open("tests/test_data/raw/ukpga-Geo3-49-126-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def parsed_content(xml_parser, sample_xml):
    """Parse the sample content and return results."""
    soup = BeautifulSoup(sample_xml, "xml")
    return xml_parser.parse_content(soup)


def test_parse_basic_metadata(xml_parser, sample_xml):
    """Test basic metadata extraction."""
    soup = BeautifulSoup(sample_xml, "xml")
    sections, schedules, commentaries = xml_parser.parse_content(soup)

    assert len(sections) == 14
    assert len(schedules) == 0
    assert len(commentaries) == 1


def test_extent_mapping(parsed_content):
    """Test the mapping of geographical extents."""
    sections = parsed_content[0]
    section = sections.get(
        "http://www.legislation.gov.uk/id/ukpga/Geo3/49/126/section/1."
    )
    assert section is not None
    assert section.extent == [GeographicalExtent.UK]


def test_parse_section_structure(parsed_content):
    """Test parsing of section structure."""
    sections, _, _ = parsed_content

    section = sections.get(
        "http://www.legislation.gov.uk/id/ukpga/Geo3/49/126/section/1."
    )
    assert section is not None
    assert section.number == "1"
    assert section.legislation_title == "Sale of Offices Act 1809 (repealed)"
    assert section.extent == [GeographicalExtent.UK]


def test_parse_commentary_structure(parsed_content):
    """Test parsing of commentary structure."""
    _, _, commentaries = parsed_content

    commentary = commentaries.get("key-e4a86527436e8a939be9d94aa5ca7ee0")
    assert commentary is not None
    assert commentary.type == "F"


@pytest.mark.xfail(reason="Stats regarding number of provisions are unclear")
def test_number_of_provisions(parsed_content, sample_xml):
    """Test the number of parsed provisions matches the provision stats attribute."""
    soup = BeautifulSoup(sample_xml, "xml")

    number_of_provisions = int(soup.find("ukm:TotalParagraphs")["Value"])
    number_sections = int(soup.find("ukm:BodyParagraphs")["Value"])
    number_schedule = int(soup.find("ukm:ScheduleParagraphs")["Value"])

    sections, schedules, commentaries = parsed_content
    total_provisions = len(sections) + len(schedules)

    assert number_sections == len(sections)
    assert number_schedule == len(schedules)
    assert total_provisions == number_of_provisions
