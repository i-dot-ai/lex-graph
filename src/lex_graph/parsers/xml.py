from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from lex_graph.reference_finders.base import ReferenceFinder
from lex_graph.types import (
    Commentary,
    GeographicalExtent,
    Legislation,
    Schedule,
    Section,
)


class XMLParser(ABC):
    """Abstract base class for building legislation XML parsers.

    Top level structure: https://github.com/legislation/clml-schema/blob/main/schema/schemaLegislationCore.xsd
    Main: https://github.com/legislation/clml-schema/blob/main/schema/schemaLegislationMain.xsd
    """

    def __init__(self, reference_finder: ReferenceFinder):
        self.reference_finder = reference_finder

        self.extent_mapping = {
            "E": GeographicalExtent.E,
            "W": GeographicalExtent.W,
            "S": GeographicalExtent.S,
            "N.I.": GeographicalExtent.NI,
            "NI": GeographicalExtent.NI,
            "E+W+S+N.I.": GeographicalExtent.UK,
            "E+W+S+N.I": GeographicalExtent.UK,
            "E+W+S+NI": GeographicalExtent.UK,
        }

    @abstractmethod
    def parse_content(
        self, xml_soup: BeautifulSoup
    ) -> Tuple[Dict[str, Section], Dict[str, Schedule], Dict[str, Commentary]]:
        """Parse XML content into sections."""
        pass

    def _extract_text(self, element: Optional[Tag]) -> str:
        """Extract text from an element, handling None cases and cleaning text."""
        if element is None:
            return ""

        # Remove emphasis, strong and uppercase tags
        for tag in element.find_all(["Emphasis", "Strong", "Uppercase"]):
            tag.unwrap()

        # Get all text content
        text_parts = []
        for text in element.stripped_strings:
            cleaned = self._clean_text(text)
            if cleaned:
                text_parts.append(cleaned)

        content_str = " ".join(text_parts).strip("\n")

        # Remove trailing space before punctuation
        if content_str[-2:] in {" .", " ,"}:
            content_str = content_str[:-2] + content_str[-1]

        return content_str

    def _extract_date(self, element: Tag) -> Optional[date]:
        """Extract date from XML element."""
        text = self._extract_text(element)

        if not text:
            return None

        return datetime.strptime(text, "%Y-%m-%d").date()

    def _extract_value(self, element: Tag) -> str:
        """Extract value from XML element."""
        if element is None:
            return ""
        return element.get("Value", "")

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        # Remove extra whitespace and normalize spaces
        text = " ".join(text.split())
        # Remove common XML artifacts
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        return text

    def _restrict_extent_to_string(self, extent: str) -> str:
        """Convert the restrict_extent field to a string.
        If the restrict_extent is "E+W+S+N.I.", return "United Kingdom", otherwise return the list of countries separated by commas.

        Args:
            restrict_extent (_type_): The original restrict_extent field, not in a human-readable format.

        Returns:
            extent_str: The converted restrict_extent field, in a human-readable format.
        """
        mapping = {
            "E": "England",
            "W": "Wales",
            "S": "Scotland",
            "N.I.": "Northern Ireland",
            "N.I": "Northern Ireland",
            "NI": "Northern Ireland",
        }

        if extent == "E+W+S+N.I.":
            return "United Kingdom"
        elif extent == "E+W+S+N.I":
            return "United Kingdom"
        elif extent == "E+W+S+NI":
            return "United Kingdom"
        elif extent == "":
            return ""
        else:
            return ", ".join([mapping[extent] for extent in extent.split("+")])

    def map_extent(self, extent: str) -> List[GeographicalExtent]:
        """Convert the extent content field to a unoform string.

        Args:
            extent (str): The original restrict_extent field, not in a human-readable format.

        Returns:
            extent_str: The converted restrict_extent field, in a human-readable format.
        """

        try:
            if extent in self.extent_mapping:
                return [self.extent_mapping[extent]]
            elif extent == "":
                return [GeographicalExtent.NONE]
            elif extent is None:
                return [GeographicalExtent.NONE]
            else:
                return [self.extent_mapping[extent] for extent in extent.split("+")]
        except KeyError:
            return [GeographicalExtent.NONE]
        except Exception as e:
            print(f"Unkown Extent Mapping Error: {e}")
            return [GeographicalExtent.NONE]

    def parse(self, xml_content: str) -> Legislation:
        """Parse XML content into a Legislation object."""

        # Convert XML content to BeautifulSoup object
        soup = BeautifulSoup(xml_content, "xml")

        # Extract the standard metadata
        id = soup.find("Legislation").get("IdURI")
        uri = self._extract_text(soup.find("dc:identifier"))
        title = self._extract_text(soup.find("dc:title"))
        description = self._extract_text(soup.find("dc:description"))
        valid_date = self._extract_date(soup.find("dct:valid"))
        modified_date = self._extract_date(soup.find("dc:modified"))
        publisher = self._extract_text(soup.find("dc:publisher"))
        category = self._extract_value(soup.find("ukm:DocumentCategory"))
        type = self._extract_value(soup.find("ukm:DocumentMainType"))
        status = self._extract_value(soup.find("ukm:DocumentStatus"))

        legislation_element = soup.find("Legislation")
        if legislation_element.has_attr("NumberOfProvisions"):
            number_of_provisions = legislation_element["NumberOfProvisions"]
        else:
            number_of_provisions = None
        if legislation_element.has_attr(
            "RestrictExtent"
        ):  # Check if restrict extent is present. Unclear why some of the XMLs have it and some don't
            extent = legislation_element["RestrictExtent"]
        else:
            extent = ""

        enactment_date = soup.find("ukm:EnactmentDate")
        if enactment_date is not None:
            enactment_date = datetime.strptime(
                enactment_date.get("Date"), "%Y-%m-%d"
            ).date()  # Made / Laid for secondary?

        # Parse content into sections, schedules and citations
        sections, schedules, commentaries = self.parse_content(soup)

        # Return Legislation object
        return Legislation(
            id=id,
            uri=uri,
            title=title,
            description=description,
            enactment_date=enactment_date,
            valid_date=valid_date,
            modified_date=modified_date,
            publisher=publisher,
            category=category,
            type=type,
            status=status,
            extent=self.map_extent(extent),
            number_of_provisions=int(number_of_provisions),
            sections=list(sections.values()),
            schedules=list(schedules.values()),
            commentaries=commentaries,
        )
