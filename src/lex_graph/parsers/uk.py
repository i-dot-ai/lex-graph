from typing import Dict, List, Tuple

from bs4 import BeautifulSoup, Tag

from lex_graph.parsers.xml import XMLParser
from lex_graph.types import Commentary, CommentaryCitation, Paragraph, Schedule, Section


class UKXMLParser(XMLParser):
    """Parser for UK legislation XML format.

    Structure: https://github.com/legislation/clml-schema/blob/main/schema/schemaLegislationStructure.xsd
    Content: https://github.com/legislation/clml-schema/blob/main/schema/schemaLegislationContents.xsd
    """

    def parse_content(
        self, xml_soup: BeautifulSoup
    ) -> Tuple[Dict[str, Section], Dict[str, Schedule], Dict[str, Commentary]]:
        sections = {}
        schedules = {}
        commentaries = {}

        # Extract metadata
        title = xml_soup.find("dc:title").text
        extent = xml_soup.find("Legislation").get("RestrictExtent", "")

        # Extract and parse sections from the body with citable Ids
        body = xml_soup.find("Body")
        for section_elem in body.find_all("P1", attrs={"IdURI": True}):
            section = self._parse_section(section_elem, extent, title)
            sections[section.id] = section

        # Extract and parse schedules from the body with citable Ids
        schedule_body = xml_soup.find("Schedules")
        if schedule_body:
            extent = schedule_body.get("RestrictExtent", extent)
            for schedule_elem in schedule_body.find_all(
                "Schedule", attrs={"IdURI": True}
            ):
                schedule = self._parse_schedule(schedule_elem, extent, title)
                schedules[schedule.id] = schedule

        # Extract and parse commentaries
        commentary = xml_soup.find("Commentaries")
        if commentary:
            for commentary_elem in commentary.find_all(
                "Commentary", attrs={"id": True}
            ):
                commentary = self._parse_commentary(commentary_elem)
                commentaries[commentary.id] = commentary

        return sections, schedules, commentaries

    def _parse_schedule(
        self, element: Tag, extent: str, legislation_title: str
    ) -> Schedule:
        """Parse a schedule element."""

        # Get title for schedule if available
        if self._extract_text(element.find("Title")):
            schedule_title = self._extract_text(element.find("Title"))
        else:
            schedule_title = ""

        schedule = Schedule(
            id=element.get("IdURI"),
            uri=element.get("DocumentURI"),
            number=element.get("id").lstrip("schedule-").strip("."),
            text=schedule_title,
            extent=self.map_extent(extent),
            legislation_title=legislation_title,
        )

        # Parse paragraphs with citable Ids
        for p1_elem in element.find_all("P1", attrs={"IdURI": True}):  # Was P1
            paragraph = self._parse_paragraph(p1_elem, legislation_title)
            schedule.add_paragraph(paragraph)

        # Find references in title text
        schedule.references = self.reference_finder.find_references(
            schedule.id, schedule.text
        )

        # Find commentary refs for the schedule object
        schedule.commentary_refs = self._parse_commentary_refs(element)

        return schedule

    def _parse_section(
        self, element: Tag, extent: str, legislation_title: str
    ) -> Section:
        """Parse a section element."""

        # Get title for section if available
        parent = element.parent
        # Try to get local extent from parent Part, fall back to global extent
        local_extent = self._get_parent_extent(element) or extent

        if parent.name == "P1group":
            section_title = self._extract_text(parent.find("Title"))
        else:
            section_title = ""

        section_id = element.get("IdURI")

        section = Section(
            id=section_id,
            uri=element.get("DocumentURI"),
            number=element.get("id").lstrip("section-").strip("."),
            text=section_title,
            extent=self.map_extent(local_extent),
            legislation_title=legislation_title,
        )

        # Parse paragraphs with citable Ids
        for p2_elem in element.find_all(["P2"], recursive=True, attrs={"IdURI": True}):
            paragraph = self._parse_paragraph(p2_elem, legislation_title)
            section.add_paragraph(paragraph)

        # Find references in title text
        section.references = self.reference_finder.find_references(
            section.id, section.text
        )

        # Find commentary refs for the section itself
        section.commentary_refs = self._parse_commentary_refs(element)

        return section

    def _parse_nested_commentaries(
        self, element: Tag, paragraph: Paragraph
    ) -> List[Commentary]:
        """Find nested P3 paragraphs and extract their commentary."""

        nested_p3_paragraphs = element.find_all(
            "P3", recursive=True, attrs={"IdURI": True}
        )
        for nested_p3_paragraphs in nested_p3_paragraphs:
            if nested_p3_paragraphs and nested_p3_paragraphs.find("P3para"):
                for p3_para in nested_p3_paragraphs.find_all("P3para", recursive=True):
                    if p3_para:
                        text = self._extract_text(p3_para)
                        if text:
                            paragraph.references.extend(
                                self.reference_finder.find_references(
                                    paragraph.id, self._extract_text(p3_para)
                                )
                            )
                        if isinstance(
                            p3_para, Tag
                        ):  # Check if the element is a tag, otherwise it's a string
                            p3_commentary = self._parse_commentary_refs(p3_para)
                            paragraph.commentary_refs.extend(p3_commentary)
        return paragraph

    def _parse_paragraph(self, element: Tag, legislation_title: str) -> Paragraph:
        """Parse a paragraph element preserving exact text structure."""

        # Get the main text content
        text_parts = []

        # Add the main paragraph text
        p2para = element.find_all("P2para")
        if p2para:
            for p2p in p2para:
                text_parts.append(self._extract_text(p2p))

        # Process any bullet lists
        for list_elem in element.find_all("UnorderedList"):
            for item in list_elem.find_all("ListItem"):
                text_parts.append(f"* {self._extract_text(item)}")

        # Create paragraph with proper formatting
        text = "\n".join(text_parts)
        paragraph = Paragraph(
            id=element.get("IdURI"),
            uri=element.get("DocumentURI"),
            number=self._extract_text(element.find("Pnumber")).strip("."),
            text=text,
            legislation_title=legislation_title,
            paragraph_id=element.get(
                "id"
            ),  # E.g., "section-1-3-c" for linking to commentary/labelling
        )

        # Find commentary references
        paragraph.commentary_refs = self._parse_commentary_refs(element)

        # Find references
        paragraph.references = self.reference_finder.find_references(paragraph.id, text)

        paragraph = self._parse_nested_commentaries(element, paragraph)

        return paragraph

    def _parse_commentary(self, element: Tag) -> Commentary:
        """
        Parse a commentary containing element.
        https://legislation.github.io/clml-schema/userguide.html#commentaries
        """

        # Extract type
        commentary_type = element.get("Type")

        # Higher level citations
        citation_elements = element.find_all("Citation", attrs={"URI": True})
        citations = []
        for citation in citation_elements:
            citation = CommentaryCitation(
                id=citation.get("id"),
                uri=citation.get("URI"),
                type=commentary_type,
                context=citation.text,
                section_ref=citation.get("SectionRef", citation.get("StartSectionRef")),
                citation_ref=citation.get("CitationRef", "SelfReference"),
                citation_type="primary",
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
                section_ref=citation_sub_ref.get(
                    "SectionRef", citation_sub_ref.get("StartSectionRef")
                ),
                citation_ref=citation_sub_ref.get("CitationRef", "SelfReference"),
                citation_type="sub_reference",
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
        for commentary_ref in element.find_all(
            ["CommentaryRef"], recursive=True, attrs={"Ref": True}
        ):
            commentary_refs.append(commentary_ref.get("Ref"))
        return commentary_refs

    def _get_parent_extent(self, element: Tag) -> str:
        """Get the RestrictExtent value from the parent Part element."""
        current = element.parent
        while current is not None:
            if current.name == "Part":
                return current.get("RestrictExtent", "")
            current = current.parent
        return ""  # Return empty string if no Part parent found
