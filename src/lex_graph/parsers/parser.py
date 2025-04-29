from bs4 import BeautifulSoup

from lex_graph.parsers.eu import EUXMLParser
from lex_graph.parsers.uk import UKXMLParser
from lex_graph.parsers.xml import XMLParser
from lex_graph.reference_finders.pattern import (
    EUReferencePatterns,
    PatternReferenceFinder,
    UKReferencePatterns,
)
from lex_graph.types import Legislation


class LegislationParser:
    """Main interface for parsing legislation documents."""

    @staticmethod
    def create_parser(xml_content: str) -> XMLParser:
        """Create appropriate parser based on XML content."""
        if not isinstance(xml_content, str):
            raise TypeError("xml_content must be a string")
        soup = BeautifulSoup(xml_content, "xml")

        if soup.find("EURetained"):
            return EUXMLParser(PatternReferenceFinder(EUReferencePatterns()))
        return UKXMLParser(PatternReferenceFinder(UKReferencePatterns()))

    def parse(self, xml_content: str) -> Legislation:
        """Parse legislation XML content."""
        parser = self.create_parser(xml_content)
        return parser.parse(xml_content)
