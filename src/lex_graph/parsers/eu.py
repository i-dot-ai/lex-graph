from typing import Dict, List, Tuple

from bs4 import BeautifulSoup, Tag

from lex_graph.exceptions import MissingIDError
from lex_graph.parsers.xml import XMLParser
from lex_graph.types import Commentary, CommentaryCitation, Paragraph, Schedule, Section


class EUXMLParser(XMLParser):
    """Parser for EU legislation XML format.

    Structure: https://github.com/legislation/clml-schema/blob/main/schema/schemaLegislationStructureEU.xsd
    Content: https://github.com/legislation/clml-schema/blob/main/schema/schemaLegislationContentsEU.xsd
    """

    def parse_content(
        self, xml_soup: BeautifulSoup
    ) -> Tuple[Dict[str, Section], Dict[str, Schedule], Dict[str, Commentary]]:
        sections = {}
        schedules = {}
        commentaries = {}

        # TODO: Parse EU XML format better
        # Extra EU Metadata
        # EUPreamble
        # EUBody
        # Schedules
        # Amendments

        # Extract Extent from "Part" element
        leg = xml_soup.find("Legislation")
        extent = leg.get("RestrictExtent")
        legislation_title = xml_soup.find("dc:title").text

        # Extract sections from the body
        body = xml_soup.find("EUBody")
        for div_elem in body.find_all("P1", attrs={"IdURI": True}):
            section = self._parse_division(div_elem, extent, legislation_title)
            sections[section.id] = section

            # Extract schedules from the body with citable Ids
        schedule_body = xml_soup.find("Schedules")
        if schedule_body:
            for schedule_elem in schedule_body.find_all(
                "Schedule", attrs={"IdURI": True}
            ):
                try:
                    schedule = self._parse_schedule(
                        schedule_elem, extent, legislation_title
                    )
                    schedules[schedule.id] = schedule
                except MissingIDError as e:
                    print(f"Missing ID Error: {e}")

        # Extract and parse commentaries
        commentary = xml_soup.find("Commentaries")
        if commentary:
            for commentary_elem in commentary.find_all(
                "Commentary", attrs={"id": True}
            ):
                commentary = self._parse_commentary(commentary_elem)
                commentaries[commentary.id] = commentary

        return sections, schedules, commentaries

    def _parse_division(
        self, element: Tag, extent: str, legislation_title: str
    ) -> Section:
        """Parse a division element."""
        section = Section(
            id=element.get("IdURI"),  # id or IdURI
            uri=element.get("DocumentURI"),
            number=self._extract_text(element.find("Pnumber")).strip("."),
            text=self._extract_text(element.find("P1para")),
            extent=self.map_extent(extent),
            paragraphs=[],
            citations=[],
            legislation_title=legislation_title,
        )

        # Parse paragraphs
        for p_elem in element.find_all(
            "P", attrs={"IdURI": True}
        ):  # P1para works but doesn't have ID
            paragraph = self._parse_paragraph(p_elem, legislation_title)
            section.add_paragraph(paragraph)

        # Find references in title
        section.references = self.reference_finder.find_references(
            section.id, section.text
        )

        return section

    def _parse_paragraph(self, element: Tag, legislation_title: str) -> Paragraph:
        """Parse a paragraph element."""
        para_id = element.get("IdURI")
        text = self._extract_text(element)
        paragraph = Paragraph(
            id=para_id,
            uri=element.get("DocumentURI"),
            number=str(element.parent.find_all("P").index(element) + 1),
            text=text,
            legislation_title=legislation_title,
            paragraph_id=element.get("id"),
        )

        # Find references
        paragraph.references = self.reference_finder.find_references(para_id, text)

        # Find commentary references
        paragraph.commentary_refs = self._parse_commentary_refs(element)

        return paragraph

    def _parse_schedule(
        self, element: Tag, extent: str, legislation_title: str
    ) -> Section:
        """Parse a section element."""

        # Get title for section if available
        parent = element.parent

        if parent.name == "P1group":
            schedule_title = self._extract_text(parent.find("Title"))
        elif parent.name == "Schedules":
            schedule_title = self._extract_text(parent.find("Title"))
        else:
            schedule_title = self._extract_text(element.find("tbody"))

        schedule = Schedule(
            id=element.get("IdURI"),
            uri=element.get("DocumentURI"),
            number=self._extract_text(element.find("Pnumber")).strip("."),
            text=schedule_title,
            extent=self.map_extent(extent),
            paragraphs=[],
            citations=[],
            legislation_title=legislation_title,
        )

        # Parse text from the schedule
        for p1_elem in element.find_all(
            "P", attrs={"IdURI": True}
        ):  # The text body is actually contained within "tbody" so this doesn't return anything
            try:
                paragraph = self._parse_paragraph(p1_elem, legislation_title)
                schedule.add_paragraph(paragraph)

            except MissingIDError as e:
                print(f"Missing ID Error: {e}")

        # Find references in title text
        schedule.references = self.reference_finder.find_references(
            schedule.id, schedule.text
        )

        return schedule

    def _parse_commentary(self, element: Tag) -> Commentary:
        """
        Parse a commentary containing element.
        https://legislation.github.io/clml-schema/userguide.html#commentaries
        """

        # Extract type
        commentary_type = element.get("Type")

        # Higher level citations
        citation_elements = element.find_all(
            "Citation", attrs={"URI": True}
        )  # Here we can either make it so attrs is also 'id' or we can substitute ID with the URI, or use parent id?
        citations = []
        for citation in citation_elements:
            citation = CommentaryCitation(
                id=citation.get(
                    "id", citation.get("URI")
                ),  # This is a temporary fix, we need to decide whether to use URI or ID
                uri=citation.get("URI"),
                type=commentary_type,
                context=citation.text,
            )
            citations.append(citation)

        # Lower level citation
        citation_subref_elements = element.find_all(
            "CitationSubRef", attrs={"URI": True}
        )
        for citation_sub_ref in citation_subref_elements:
            citation_sub_ref = CommentaryCitation(
                id=citation_sub_ref.get("id"),
                uri=citation_sub_ref.get("URI"),
                type=commentary_type,
                context=citation_sub_ref.text,
            )
            citations.append(citation_sub_ref)

        commentary = Commentary(
            id=element.get("id"),
            type=commentary_type,
            citations=citations,
            text=self._extract_text(element),
        )

        return commentary

    def _parse_commentary_refs(self, element: Tag) -> List[str]:
        """Extract citations from the element."""

        commentary_refs = []
        for commentary_ref in element.find_all("CommentaryRef", attrs={"Ref": True}):
            commentary_refs.append(commentary_ref.get("Ref"))

        return commentary_refs
