import pytest
from bs4 import BeautifulSoup

from lex_graph.parsers.uk import UKXMLParser
from lex_graph.reference_finders.pattern import (
    PatternReferenceFinder,
    UKReferencePatterns,
)
from lex_graph.types import FreeTextReference, GeographicalExtent


@pytest.fixture
def parser():
    return UKXMLParser(PatternReferenceFinder(UKReferencePatterns()))


@pytest.fixture
def sample_xml():
    with open("tests/test_data/raw/ukpga-2004-34-revised-data.xml", "r") as file:
        xml_content = file.read()
    return xml_content


@pytest.fixture
def parsed_content(parser, sample_xml):
    """Parse the sample content and return results."""
    soup = BeautifulSoup(sample_xml, "xml")
    return parser.parse_content(soup)


def test_parse_basic_metadata(parser, sample_xml):
    """Test basic metadata extraction."""
    soup = BeautifulSoup(sample_xml, "xml")
    sections, schedules, commentaries = parser.parse_content(soup)

    assert soup.find("dc:title").text == "Housing Act 2004"
    assert soup.find("Legislation").get("RestrictExtent") == "E+W+S+N.I."


def test_extent_mapping(parser):
    """Test the mapping of geographical extents."""
    # Test individual countries
    assert parser.map_extent("E") == [GeographicalExtent.E]
    assert parser.map_extent("W") == [GeographicalExtent.W]
    assert parser.map_extent("S") == [GeographicalExtent.S]
    assert parser.map_extent("N.I.") == [GeographicalExtent.NI]

    # Test UK combinations
    assert parser.map_extent("E+W+S+N.I.") == [GeographicalExtent.UK]
    assert parser.map_extent("E+W+S+NI") == [GeographicalExtent.UK]

    # Test empty and invalid cases
    assert parser.map_extent("") == [GeographicalExtent.NONE]
    assert parser.map_extent(None) == [GeographicalExtent.NONE]
    assert parser.map_extent("INVALID") == [GeographicalExtent.NONE]


def test_parse_section_structure(parsed_content):
    """Test parsing of section structure."""
    sections, _, _ = parsed_content

    # Test section 1 structure
    section = sections.get("http://www.legislation.gov.uk/id/ukpga/2004/34/section/1")
    assert section is not None
    assert section.number == "1"
    assert section.legislation_title == "Housing Act 2004"
    assert section.extent == [
        GeographicalExtent.E,
        GeographicalExtent.W,
    ]  # From RestrictExtent attribute

    # Verify paragraphs
    paragraphs = list(section.paragraphs)
    assert len(paragraphs) == 8  # Eight P2 paragraphs in section 1

    # Check first paragraph content
    first_para = paragraphs[0]
    assert first_para.id == "http://www.legislation.gov.uk/id/ukpga/2004/34/section/1/1"
    assert "This Part provides—" in first_para.text


def test_parse_schedule_structure(parsed_content):
    """Test parsing of schedule structure."""
    _, schedules, _ = parsed_content
    # Test schedule 1 structure
    schedule = schedules.get(
        "http://www.legislation.gov.uk/id/ukpga/2004/34/schedule/1"
    )

    assert schedule is not None
    assert schedule.number == "1"
    assert (
        schedule.text == "Procedure and appeals relating to improvement notices"
    )  # TO FIGURE OUT IF PARAGRAPH OF SCHEDULES TEXT SHOULD BE CONDENSED INTO THE PARENT SCHEDULE TEXT

    # Verify paragraphs
    paragraphs = list(schedule.paragraphs)
    assert len(paragraphs) == 20  # Twenty P1 paragraph in schedule 1

    # Check paragraph content
    first_para = paragraphs[0]
    assert (
        first_para.id
        == "http://www.legislation.gov.uk/id/ukpga/2004/34/schedule/1/paragraph/1"
    )
    assert "This paragraph applies where the specified premises" in first_para.text


def test_parse_commentary_structure(parsed_content):
    """Test parsing of commentary structure."""
    _, _, commentaries = parsed_content

    # Test commentary c2050708
    commentary = commentaries.get("c2050708")
    assert commentary is not None
    assert commentary.type == "I"

    # Check citations
    citations = commentary.citations
    assert len(citations) == 11  # Eleven citations in commentary c2050708

    # Verify first citation
    first_citation = citations[0]
    assert (
        first_citation.id == "c00005"
    )  # Because 'Citation' is parsed before 'CitationSubRef'
    assert first_citation.uri == "http://www.legislation.gov.uk/id/uksi/2006/1060"
    assert first_citation.type == "I"


def test_commentary_references(parsed_content):
    """Test extraction of commentary references from sections."""
    sections, _, _ = parsed_content

    section = sections.get("http://www.legislation.gov.uk/id/ukpga/2004/34/section/1")
    assert "c2050708" in section.commentary_refs


def test_nested_commentaries(parsed_content):
    """Test parsing of nested commentaries in paragraphs."""
    sections, _, _ = parsed_content

    section = sections.get("http://www.legislation.gov.uk/id/ukpga/2004/34/section/1")
    for paragraph in section.paragraphs:
        if paragraph.id == "http://www.legislation.gov.uk/id/ukpga/2004/34/section/1/2":
            # Check references in nested P3 paragraphs
            assert (
                FreeTextReference(source_id=paragraph.id, section="2", context="")
                in paragraph.references
            )
            assert (
                FreeTextReference(
                    source_id=paragraph.id,
                    section="604",
                    act="Housing Act 1985",
                    context="",
                )
                in paragraph.references
            )


def test_error_handling(parser):
    """Test parser error handling with invalid XML."""
    with pytest.raises(Exception):
        soup = BeautifulSoup("<invalid>XML</invalid>", "xml")
        parser.parse_content(soup)


def test_extent_extraction(parsed_content):
    """Test mapping of extent codes."""
    sections, schedules, _ = parsed_content

    # Check section extent
    section = sections.get("http://www.legislation.gov.uk/id/ukpga/2004/34/section/1")
    assert section.extent == [GeographicalExtent.E, GeographicalExtent.W]

    # Check schedule extent
    schedule = schedules.get(
        "http://www.legislation.gov.uk/id/ukpga/2004/34/schedule/1"
    )
    assert schedule.extent == [
        GeographicalExtent.E,
        GeographicalExtent.W,
    ]  # From RestrictExtent attribute in Schedules tag


@pytest.mark.xfail(reason="Stats regarding number of provisions are unclear")
def test_number_of_provisions(parsed_content, sample_xml):
    """Test the number of parsed provisions matches the provision stats attribute."""
    soup = BeautifulSoup(sample_xml, "xml")

    number_sections = int(soup.find("ukm:BodyParagraphs")["Value"])
    number_schedule = int(soup.find("ukm:ScheduleParagraphs")["Value"])

    sections, schedules, _ = parsed_content

    assert number_sections == len(sections)
    assert number_schedule == len(schedules)
