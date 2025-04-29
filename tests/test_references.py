import os

import pytest

from lex_graph.reference_finders.llm import GPTReferenceFinder
from lex_graph.reference_finders.pattern import (
    EUReferencePatterns,
    PatternReferenceFinder,
    UKReferencePatterns,
)
from lex_graph.types import FreeTextReference


@pytest.fixture
def uk_reference_finder():
    return PatternReferenceFinder(UKReferencePatterns())


@pytest.fixture
def eu_reference_finder():
    return PatternReferenceFinder(EUReferencePatterns())


@pytest.fixture
def reference_finder_gpt():
    if os.getenv("AZURE_OPENAI_API_KEY") is None:
        pytest.skip(
            "AZURE_OPENAI_API_KEY is not set, unable to test GPTReferenceFinder"
        )
    return GPTReferenceFinder()


test_cases = [
    (
        "Refer to section 45 of the Data Protection Act 2018 and section 46 of the Freedom of Information Act 2000 for details.",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Data Protection Act 2018",
                section="45",
                context="",
            ),
            FreeTextReference(
                source_id="test-doc",
                act="Freedom of Information Act 2000",
                section="46",
                context="",
            ),
        ],
    ),
    (
        "as referred to in section 78 of this Act",
        [FreeTextReference(source_id="test-doc", section="78", context="")],
    ),
    (
        "The appropriate national authority may by regulations make such provision as it considers appropriate for supplementing the provisions of this section and section 73, and in particular",
        [FreeTextReference(source_id="test-doc", section="73", context="")],
    ),
    (
        "sections 32 to 36 (enforcement);",
        [
            FreeTextReference(source_id="test-doc", section="32", context=""),
            FreeTextReference(source_id="test-doc", section="33", context=""),
            FreeTextReference(source_id="test-doc", section="34", context=""),
            FreeTextReference(source_id="test-doc", section="35", context=""),
            FreeTextReference(source_id="test-doc", section="36", context=""),
        ],
    ),
    (
        "Part 9 of the Housing Act 1985 (c. 68) (demolition orders and slum clearance);",
        [FreeTextReference(source_id="test-doc", act="Housing Act 1985", context="")],
    ),
    (
        "section 115(2) of the Crime and Disorder Act 1998 (c. 37) after paragraph (d) insert—",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Crime and Disorder Act 1998",
                section="115",
                context="",
            )
        ],
    ),
    (
        "Subsection (5) applies where, under section 308 of the Housing Act 1985 (c. 68) (owner's re-development proposals), the local housing authority have approved proposals for the re-development of land.",
        [
            FreeTextReference(
                source_id="test-doc", act="Housing Act 1985", section="308", context=""
            )
        ],
    ),
    (
        "Refer to sections 92, 93, or 94.",
        [
            FreeTextReference(source_id="test-doc", section="92", context=""),
            FreeTextReference(source_id="test-doc", section="93", context=""),
            FreeTextReference(source_id="test-doc", section="94", context=""),
        ],
    ),
    (
        "See sections 12, 13 and 14 for more details.",
        [
            FreeTextReference(source_id="test-doc", section="12", context=""),
            FreeTextReference(source_id="test-doc", section="13", context=""),
            FreeTextReference(source_id="test-doc", section="14", context=""),
        ],
    ),
    (
        "The provisions are— a the following provisions of this Act— i this Part, ii Part 2 (licensing of HMOs), iii Part 3 (selective licensing of other houses), and iv Chapters 1 and 2 of Part 4 (management orders); b Part 9 of the Housing Act 1985 (c. 68) (demolition orders and slum clearance); c Part 7 of the Local Government and Housing Act 1989 (c. 42) (renewal areas); and d article 3 of the Regulatory Reform (Housing Assistance) (England and Wales) Order 2002 ( S.I. 2002/1860).",
        [
            FreeTextReference(source_id="test-doc", act="Housing Act 1985", context=""),
            FreeTextReference(
                source_id="test-doc",
                act="Local Government and Housing Act 1989",
                context="",
            ),
        ],
    ),
    (
        "This paragraph applies to registered social landlords which are industrial and provident societies. * “ qualified auditor ” means a person who is a qualified auditor for the purposes of the Friendly and Industrial and Provident Societies Act 1968; * “ year of account ” has the meaning given by section 21(1) of that Act.",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Friendly and Industrial and Provident Societies Act 1968",
                section="21",
                context="",
            )
        ],
    ),
    (
        "Expressions used in this Part of this Schedule and in the Local Land Charges Act 1975",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Local Land Charges Act 1975",
                context="",
            )
        ],
    ),
    (
        "Act as a result of an amendment to that Act made by the Criminal Justice and Courts Act 2015",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Criminal Justice and Courts Act 2015",
                context="",
            )
        ],
    ),
    (
        "Substitution of special drawing rights in limitation provisions of Carriage of Goods by Sea Act 1971",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Carriage of Goods by Sea Act 1971",
                context="",
            )
        ],
    ),
]

eu_test_cases = [
    (
        "Refer to Article 5 of the Treaty on European Union and Article 6 of the Treaty on the Functioning of the European Union for details.",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Treaty on European Union",
                section="5",
                context="",
            ),
            FreeTextReference(
                source_id="test-doc",
                act="Treaty on the Functioning of the European Union",
                section="6",
                context="",
            ),
        ],
    ),
    (
        "as referred to in Article 78 of this Regulation",
        [FreeTextReference(source_id="test-doc", section="78", context="")],
    ),
    (
        "The appropriate authority may by regulations make such provision as it considers appropriate for supplementing the provisions of this Article and Article 73, and in particular",
        [FreeTextReference(source_id="test-doc", section="73", context="")],
    ),
    (
        "Articles 32 to 36 (enforcement);",
        [
            FreeTextReference(source_id="test-doc", section="32", context=""),
            FreeTextReference(source_id="test-doc", section="33", context=""),
            FreeTextReference(source_id="test-doc", section="34", context=""),
            FreeTextReference(source_id="test-doc", section="35", context=""),
            FreeTextReference(source_id="test-doc", section="36", context=""),
        ],
    ),
    (
        "Part 9 of the Regulation (EU) 2016/679 (General Data Protection Regulation);",
        [
            FreeTextReference(
                source_id="test-doc", act="Regulation (EU) 2016/679", context=""
            )
        ],
    ),
    (
        "Article 115(2) of the Directive 2006/112/EC (VAT Directive) after paragraph (d) insert—",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Directive 2006/112/EC",
                section="115",
                context="",
            )
        ],
    ),
    (
        "Subsection (5) applies where, under Article 308 of the Regulation (EU) 2016/679 (General Data Protection Regulation), the authority has approved proposals for the re-development of data protection measures.",
        [
            FreeTextReference(
                source_id="test-doc",
                act="Regulation (EU) 2016/679",
                section="308",
                context="",
            )
        ],
    ),
    (
        "Refer to Articles 92, 93, or 94.",
        [
            FreeTextReference(source_id="test-doc", section="92", context=""),
            FreeTextReference(source_id="test-doc", section="93", context=""),
            FreeTextReference(source_id="test-doc", section="94", context=""),
        ],
    ),
    (
        "See Articles 12, 13 and 14 for more details.",
        [
            FreeTextReference(source_id="test-doc", section="12", context=""),
            FreeTextReference(source_id="test-doc", section="13", context=""),
            FreeTextReference(source_id="test-doc", section="14", context=""),
        ],
    ),
    (
        "The provisions are— a the following provisions of this Regulation— i this Part, ii Part 2 (licensing of data controllers), iii Part 3 (selective licensing of data processors), and iv Chapters 1 and 2 of Part 4 (management orders); b Part 9 of the Regulation (EU) 2016/679 (General Data Protection Regulation); c Part 7 of the Directive 2002/58/EC (ePrivacy Directive); and d article 3 of the Regulation (EU) 2018/1725 (Data Protection Regulation for EU institutions).",
        [
            FreeTextReference(
                source_id="test-doc", act="Regulation (EU) 2016/679", context=""
            ),
            FreeTextReference(
                source_id="test-doc",
                act="Directive 2002/58/EC",
                context="",
            ),
        ],
    ),
]


@pytest.mark.parametrize("text, expected_references", test_cases)
def test_pattern_reference_finder(uk_reference_finder, text, expected_references):
    source_id = "test_doc"
    references = uk_reference_finder.find_references(source_id, text)

    assert len(references) == len(
        expected_references
    ), f"Expected {len(expected_references)} references, but got {len(references)}"
    for ref, expected in zip(references, expected_references):
        assert (
            ref.act == expected.act
        ), f"Expected act {expected.act}, but got {ref.act}"
        assert (
            ref.section == expected.section
        ), f"Expected section {expected.section}, but got {ref.section}"


@pytest.mark.skip("GPTReferenceFinder is not complete yet")
@pytest.mark.parametrize("text, expected_references", test_cases)
def test_gpt_reference_finder(reference_finder_gpt, text, expected_references):
    source_id = "test_doc"
    references = reference_finder_gpt.find_references(source_id, text)

    assert len(references) == len(
        expected_references
    ), f"Expected {len(expected_references)} references, but got {len(references)}"
    for ref, expected in zip(references, expected_references):
        assert (
            ref.act == expected.act
        ), f"Expected act {expected.act}, but got {ref.act}"
        assert (
            ref.section == expected.section
        ), f"Expected section {expected.section}, but got {ref.section}"


@pytest.mark.xfail(reason="EU reference finder is not complete yet")
@pytest.mark.parametrize("text, expected_references", eu_test_cases)
def test_eu_pattern_reference_finder(eu_reference_finder, text, expected_references):
    source_id = "test_doc"
    references = eu_reference_finder.find_references(source_id, text)

    assert len(references) == len(
        expected_references
    ), f"Expected {len(expected_references)} references, but got {len(references)}"
    for ref, expected in zip(references, expected_references):
        assert (
            ref.act == expected.act
        ), f"Expected act {expected.act}, but got {ref.act}"
        assert (
            ref.section == expected.section
        ), f"Expected section {expected.section}, but got {ref.section}"


@pytest.mark.skip("GPTReferenceFinder is not complete yet")
@pytest.mark.xfail(reason="EU reference finder is not complete yet")
@pytest.mark.parametrize("text, expected_references", eu_test_cases)
def test_eu_gpt_reference_finder(reference_finder_gpt, text, expected_references):
    source_id = "test_doc"
    references = reference_finder_gpt.find_references(source_id, text)

    assert len(references) == len(
        expected_references
    ), f"Expected {len(expected_references)} references, but got {len(references)}"
    for ref, expected in zip(references, expected_references):
        assert (
            ref.act == expected.act
        ), f"Expected act {expected.act}, but got {ref.act}"
        assert (
            ref.section == expected.section
        ), f"Expected section {expected.section}, but got {ref.section}"
