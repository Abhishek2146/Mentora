"""
Unit tests for syllabus structure helpers and schema mapping.

Covers the shared (stdlib-only) pipeline helpers in
app.services.syllabus_structure -- pseudo-unit detection, hours
coercion, parsed-data validation/cleaning, structured RAG document
building, retrieval-context formatting and tutor prompt grounding --
plus the frontend-facing ``units`` computed field on SyllabusOut.

These tests do NOT require Chroma, HuggingFace, or a live LLM.
"""
from types import SimpleNamespace

import pytest

from app.schemas.syllabus import (
    ChapterOut,
    SubjectWithChapters,
    SyllabusOut,
    SyllabusStatus,
)
from app.services.syllabus_structure import (
    TUTOR_NOT_FOUND_MESSAGE,
    build_tutor_system_prompt,
    build_unit_rag_documents,
    clean_parsed_syllabus,
    coerce_hour_value,
    consolidate_fragmented_subjects,
    extract_unit_number,
    format_retrieval_context,
    is_pseudo_unit_heading,
    sort_chapters_by_source_order,
)


# ---------------------------------------------------------------------------
# is_pseudo_unit_heading
# ---------------------------------------------------------------------------

class TestIsPseudoUnitHeading:
    """Generic section headings must never become course units."""

    @pytest.mark.parametrize(
        "name",
        [
            "Syllabus",
            "Course Syllabus",
            "Course Contents",
            "Contents",
            "Objectives",
            "Course Objectives",
            "Learning Outcomes",
            "References",
            "Reference Books",
            "Bibliography",
            "Text Books",
            "Prescribed Textbooks",
            "Evaluation Scheme",
            "Marks Distribution",
            "Prerequisites",
            "Introduction",
            "1. Introduction",
        ],
    )
    def test_pseudo_headings_rejected(self, name):
        assert is_pseudo_unit_heading(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "Unit 5: Syllabus Overview",
            "U3 The Computer System Hardware",
            "Module 2 - Evaluation Methods",
            "Introduction to Computer",
            "Introduction to Programming",
            "Unit 2: Introduction to Computer (3 Hrs.)",
            "Computer Networks Fundamentals",
        ],
    )
    def test_real_units_and_subjects_kept(self, name):
        # Explicitly-numbered headings are always real units; longer
        # subject-like names merely CONTAIN a pseudo phrase but do not
        # equal one.
        assert is_pseudo_unit_heading(name) is False

    @pytest.mark.parametrize("bad", [None, "", "   ", 123, ["Unit 1"]])
    def test_non_string_or_empty_is_not_pseudo(self, bad):
        assert is_pseudo_unit_heading(bad) is False


# ---------------------------------------------------------------------------
# coerce_hour_value
# ---------------------------------------------------------------------------

class TestCoerceHourValue:
    def test_none_is_zero(self):
        assert coerce_hour_value(None) == 0

    @pytest.mark.parametrize(
        "raw,expected",
        [(3, 3), (0, 0), (2.9, 2), ("3", 3), ("3 Hrs.", 3),
         ("(4 Hours)", 4)],
    )
    def test_valid_values(self, raw, expected):
        assert coerce_hour_value(raw) == expected

    @pytest.mark.parametrize(
        "raw", ["abc", "no digits here", None, -5, True, [], {}, object()]
    )
    def test_invalid_values_are_zero(self, raw):
        assert coerce_hour_value(raw) == 0


# ---------------------------------------------------------------------------
# clean_parsed_syllabus
# ---------------------------------------------------------------------------

class TestCleanParsedSyllabus:
    def test_rejects_pseudo_units_but_keeps_numbered_ones(self):
        raw = {
            "subjects": [
                {
                    "name": "Intro to Computing",
                    "chapters": [
                        {"name": "Syllabus", "topics": []},
                        {"name": "Objectives", "topics": ["x"]},
                        {"name": "Introduction", "topics": []},
                        {
                            "name": "Unit 2: Introduction to Computer",
                            "topics": ["Definition", "Characteristics"],
                            "estimated_hours": "3 Hrs.",
                        },
                    ],
                }
            ]
        }
        cleaned = clean_parsed_syllabus(raw)
        chapters = cleaned["subjects"][0]["chapters"]
        assert len(chapters) == 1
        assert chapters[0]["name"] == "Unit 2: Introduction to Computer"
        assert chapters[0]["estimated_hours"] == 3
        assert chapters[0]["topics"] == ["Definition", "Characteristics"]

    def test_duplicate_chapters_removed_case_insensitive_first_wins(self):
        raw = {
            "subjects": [
                {
                    "name": "Course",
                    "chapters": [
                        {"name": "Unit 1: Basics", "topics": ["a"]},
                        {"name": "unit 1: basics", "topics": ["b"]},
                        {"name": "UNIT 1: BASICS ", "topics": ["c"]},
                    ],
                }
            ]
        }
        cleaned = clean_parsed_syllabus(raw)
        chapters = cleaned["subjects"][0]["chapters"]
        assert [c["name"] for c in chapters] == ["Unit 1: Basics"]
        assert chapters[0]["topics"] == ["a"]

    def test_topics_normalized_verbatim_deduped(self):
        raw = {
            "subjects": [
                {
                    "name": "Course",
                    "chapters": [
                        {
                            "name": "Unit 1: Networks",
                            "topics": [
                                "LAN",
                                "lan ",
                                "",
                                {"name": "WAN"},
                                {"title": "MAN"},
                                42,
                                None,
                            ],
                        }
                    ],
                }
            ]
        }
        cleaned = clean_parsed_syllabus(raw)
        topics = cleaned["subjects"][0]["chapters"][0]["topics"]
        assert topics == ["LAN", "WAN", "MAN", "42"]

    def test_nameless_chapters_dropped(self):
        raw = {
            "subjects": [
                {
                    "name": "Course",
                    "chapters": [
                        {"name": "", "topics": ["orphan"]},
                        {"name": None, "topics": []},
                        {"name": "Unit 1: Real Unit", "topics": ["t"]},
                    ],
                }
            ]
        }
        cleaned = clean_parsed_syllabus(raw)
        chapters = cleaned["subjects"][0]["chapters"]
        assert [c["name"] for c in chapters] == ["Unit 1: Real Unit"]

    def test_missing_hours_default_to_zero_never_invented(self):
        raw = {
            "subjects": [
                {
                    "name": "Course",
                    "chapters": [{"name": "Unit 1: A", "topics": ["t"]}],
                }
            ]
        }
        cleaned = clean_parsed_syllabus(raw)
        assert cleaned["subjects"][0]["chapters"][0]["estimated_hours"] == 0

    def test_subject_name_fallback_when_empty(self):
        raw = {"subjects": [{"name": "", "chapters":
                             [{"name": "Unit 1: A", "topics": []}]}]}
        cleaned = clean_parsed_syllabus(raw)
        assert cleaned["subjects"][0]["name"] == "Subject 1"

    def test_raises_when_nothing_valid_remains(self):
        raw = {
            "subjects": [
                {"name": "Course", "chapters": [{"name": "Syllabus"}]}
            ]
        }
        with pytest.raises(ValueError):
            clean_parsed_syllabus(raw)

    def test_raises_on_non_dict_input(self):
        with pytest.raises(ValueError):
            clean_parsed_syllabus(["not", "a", "dict"])
        with pytest.raises(ValueError):
            clean_parsed_syllabus(None)

    def test_raises_when_subjects_missing(self):
        with pytest.raises(ValueError):
            clean_parsed_syllabus({})


# ---------------------------------------------------------------------------
# Unit ordering and subject consolidation
# ---------------------------------------------------------------------------

class TestExtractUnitNumber:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("Unit 4: Input and Output Devices", 4),
            ("unit 10. Multimedia", 10),
            ("U3 The Computer System Hardware", 3),
            ("Module 2 - Cloud Computing", 2),
            ("Unit1 Basics", 1),
        ],
    )
    def test_numbered_headings(self, name, expected):
        assert extract_unit_number(name) == expected

    @pytest.mark.parametrize(
        "name",
        [
            "Input Devices for Unit 4",   # number not leading
            "Laboratory Works",
            "Computer Networks Fundamentals",
            "",
            None,
            42,
        ],
    )
    def test_unnumbered_or_invalid(self, name):
        assert extract_unit_number(name) is None


class TestSortChaptersBySourceOrder:
    def test_sorts_by_leading_number_unnumbered_last(self):
        chapters = [
            {"name": "Laboratory Works"},
            {"name": "Unit 5: Data Communication"},
            {"name": "Unit 10: Multimedia"},
            {"name": "Unit 4: Input Devices"},
        ]
        sort_chapters_by_source_order(chapters)
        assert [c["name"] for c in chapters] == [
            "Unit 4: Input Devices",
            "Unit 5: Data Communication",
            "Unit 10: Multimedia",
            "Laboratory Works",
        ]

    def test_numeric_not_lexicographic(self):
        chapters = [{"name": f"Unit {n}: X"} for n in (10, 2, 1, 11, 20)]
        sort_chapters_by_source_order(chapters)
        assert [c["name"] for c in chapters] == [
            "Unit 1: X", "Unit 2: X", "Unit 10: X",
            "Unit 11: X", "Unit 20: X",
        ]

    def test_empty_list_is_noop(self):
        chapters = []
        sort_chapters_by_source_order(chapters)
        assert chapters == []


class TestConsolidateFragmentedSubjects:
    def _subj(self, name, names):
        return {
            "name": name,
            "description": "",
            "chapters": [{"name": n, "topics": [], "estimated_hours": 0}
                         for n in names],
        }

    def test_single_course_fragments_merged_and_ordered(self):
        subjects = [
            self._subj("Computer Science",
                       ["Unit 5: Data Communication",
                        "Unit 4: Input Devices"]),
            self._subj("Computer Fundamentals",
                       ["Unit 11: Computer Security",
                        "Unit 10: Multimedia"]),
        ]
        merged, flag = consolidate_fragmented_subjects(subjects)
        assert flag is True
        assert len(merged) == 1
        # Survivor is the first subject that holds chapters.
        assert merged[0]["name"] == "Computer Science"
        assert [c["name"] for c in merged[0]["chapters"]] == [
            "Unit 4: Input Devices",
            "Unit 5: Data Communication",
            "Unit 10: Multimedia",
            "Unit 11: Computer Security",
        ]

    def test_restarting_numbering_blocks_merge(self):
        subjects = [
            self._subj("Course A", ["Unit 1: Intro", "Unit 2: Basics"]),
            self._subj("Course B", ["Unit 1: Overview", "Unit 2: Advanced"]),
        ]
        merged, flag = consolidate_fragmented_subjects(subjects)
        assert flag is False
        assert len(merged) == 2

    def test_no_numbered_chapters_left_alone(self):
        subjects = [
            self._subj("A", ["Intro", "Body"]),
            self._subj("B", ["Extra"]),
        ]
        merged, flag = consolidate_fragmented_subjects(subjects)
        assert flag is False
        assert len(merged) == 2

    def test_single_subject_noop(self):
        subjects = [self._subj("Only", ["Unit 2: B", "Unit 1: A"])]
        merged, flag = consolidate_fragmented_subjects(subjects)
        assert flag is False
        assert merged is subjects


class TestCleanParsedSyllabusOrdering:
    def test_end_to_end_fragmented_parse_becomes_one_sorted_course(self):
        raw = {
            "subjects": [
                {
                    "name": "Computer Fundamentals",
                    "chapters": [
                        {"name": "Unit 11: Computer Security",
                         "topics": ["Viruses"]},
                        {"name": "Laboratory Works", "topics": []},
                        {"name": "Unit 10: Multimedia",
                         "topics": ["Text"]},
                    ],
                },
                {
                    "name": "Computer Science",
                    "chapters": [
                        {"name": "Unit 4: Input and Output Devices",
                         "topics": ["Keyboard"], "estimated_hours": "4 Hrs."},
                    ],
                },
            ]
        }
        cleaned = clean_parsed_syllabus(raw)
        assert len(cleaned["subjects"]) == 1
        chapters = cleaned["subjects"][0]["chapters"]
        assert [c["name"] for c in chapters] == [
            "Unit 4: Input and Output Devices",
            "Unit 10: Multimedia",
            "Unit 11: Computer Security",
            "Laboratory Works",
        ]
        assert chapters[0]["estimated_hours"] == 4


# ---------------------------------------------------------------------------
# build_unit_rag_documents
# ---------------------------------------------------------------------------

def _sample_subjects():
    return [
        {
            "name": "Intro to Computing",
            "description": "",
            "chapters": [
                {
                    "name": "Unit 2: Introduction to Computer",
                    "description": "",
                    "topics": ["Definition", "Characteristics"],
                    "estimated_hours": 3,
                },
                {
                    "name": "Unit 3: The Computer System Hardware",
                    "description": "",
                    "topics": [],
                    "estimated_hours": 0,
                },
            ],
        },
        {
            "name": "",
            "description": "",
            "chapters": [
                {
                    "name": "Unit 1: Web Concepts",
                    "description": "",
                    "topics": ["WWW"],
                    "estimated_hours": 4,
                }
            ],
        },
    ]


class TestBuildUnitRagDocuments:
    def test_one_doc_per_unit_plus_one_per_topic(self):
        docs = build_unit_rag_documents(
            syllabus_id=5,
            user_id=7,
            subjects=_sample_subjects(),
        )
        # 2 units + 2 topics + 1 unit + 1 topic = 6 documents.
        assert len(docs) == 6

    def test_metadata_traces_back_to_source(self):
        docs = build_unit_rag_documents(
            syllabus_id=5, user_id=7, subjects=_sample_subjects(),
        )
        unit_docs = [d for d in docs if "topic_title" not in d["metadata"]]
        first = unit_docs[0]
        assert first["metadata"]["user_id"] == 7
        assert first["metadata"]["syllabus_id"] == 5
        assert first["metadata"]["unit_number"] == 1
        assert first["metadata"]["unit_title"] == \
            "Unit 2: Introduction to Computer"
        assert first["metadata"]["source"] == "syllabus"

    def test_global_unit_numbering_across_subjects(self):
        docs = build_unit_rag_documents(
            syllabus_id=5, user_id=7, subjects=_sample_subjects(),
        )
        unit_numbers = sorted(
            d["metadata"]["unit_number"]
            for d in docs
            if "topic_title" not in d["metadata"]
        )
        # Numbering continues across subjects instead of restarting.
        assert unit_numbers == [1, 2, 3]

    def test_topic_docs_carry_topic_title(self):
        docs = build_unit_rag_documents(
            syllabus_id=5, user_id=7, subjects=_sample_subjects(),
        )
        topic_meta = [
            d["metadata"] for d in docs if "topic_title" in d["metadata"]
        ]
        assert {m["topic_title"] for m in topic_meta} == {
            "Definition", "Characteristics", "WWW",
        }

    def test_verbatim_numbered_headings_not_double_prefixed(self):
        docs = build_unit_rag_documents(
            syllabus_id=5, user_id=7, subjects=_sample_subjects(),
        )
        first = docs[0]["content"].splitlines()
        # The source heading already says "Unit 2: ..." - the global
        # running number must not be stacked on top of it.
        assert "Unit 2: Introduction to Computer" in first
        assert "Unit 1: Unit 2:" not in docs[0]["content"]

    def test_bare_headings_receive_running_number(self):
        subjects = [
            {
                "name": "Course",
                "chapters": [
                    {"name": "Overview", "topics": [], "estimated_hours": 0}
                ],
            }
        ]
        docs = build_unit_rag_documents(
            syllabus_id=1, user_id=1, subjects=subjects,
        )
        assert "Unit 1: Overview" in docs[0]["content"]

    def test_hours_line_only_when_stated(self):
        docs = build_unit_rag_documents(
            syllabus_id=5, user_id=7, subjects=_sample_subjects(),
        )
        stated = next(
            d for d in docs
            if d["metadata"].get("unit_title") ==
            "Unit 2: Introduction to Computer"
            and "topic_title" not in d["metadata"]
        )
        unstated = next(
            d for d in docs
            if d["metadata"].get("unit_title") ==
            "Unit 3: The Computer System Hardware"
            and "topic_title" not in d["metadata"]
        )
        assert "Hours: 3" in stated["content"]
        assert "Hours" not in unstated["content"]

    def test_course_header_falls_back_to_subject_then_generic(self):
        docs = build_unit_rag_documents(
            syllabus_id=5, user_id=7, subjects=_sample_subjects(),
        )
        named = docs[0]["content"].splitlines()[0]
        unnamed = docs[-1]["content"].splitlines()[0]
        assert named == "Course: Intro to Computing"
        assert unnamed.startswith("Course: Course")


# ---------------------------------------------------------------------------
# format_retrieval_context
# ---------------------------------------------------------------------------

def _doc(metadata=None, content="some content"):
    return SimpleNamespace(metadata=metadata or {}, page_content=content)


class TestFormatRetrievalContext:
    def test_empty_documents_return_empty_string(self):
        assert format_retrieval_context([]) == ""

    def test_blocks_carry_course_unit_topic_headers(self):
        doc = _doc(
            metadata={
                "course_name": "BSc CSIT",
                "unit_number": 2,
                "unit_title": "Introduction to Computer",
                "topic_title": "Input Devices",
                "source": "syllabus",
            },
            content="Details about input devices.",
        )
        out = format_retrieval_context([doc])
        assert out.startswith("SOURCE 1\n")
        assert "Course: BSc CSIT\n" in out
        assert "Unit 2: Introduction to Computer\n" in out
        assert "Topic: Input Devices\n" in out
        assert "Content:\nDetails about input devices." in out

    def test_legacy_metadata_keys_supported(self):
        doc = _doc(
            metadata={"subject": "Legacy S", "chapter": "Ch 1",
                      "topic": "T 1"},
            content="body",
        )
        out = format_retrieval_context([doc])
        assert "Course: Legacy S" in out
        assert "Unit: Ch 1" in out
        assert "Topic: T 1" in out

    def test_multiple_docs_numbered_sequentially(self):
        docs = [_doc(content="a"), _doc(content="b"), _doc(content="c")]
        out = format_retrieval_context(docs)
        assert "SOURCE 1\n" in out
        assert "SOURCE 2\n" in out
        assert "SOURCE 3\n" in out


# ---------------------------------------------------------------------------
# Tutor grounding prompt
# ---------------------------------------------------------------------------

class TestBuildTutorSystemPrompt:
    def test_context_blocks_include_strict_grounding_rules(self):
        prompt = build_tutor_system_prompt(
            context="SOURCE 1\nUnit 1: X",
            syllabus_selected=True,
            syllabus_title="My Course",
        )
        assert "SYLLABUS CONTEXT:" in prompt
        assert "SOURCE 1\nUnit 1: X" in prompt
        assert "Never invent" in prompt
        assert "My Course" in prompt

    def test_selected_without_context_warns_not_to_guess(self):
        prompt = build_tutor_system_prompt(context="", syllabus_selected=True)
        assert "couldn't find this topic in the uploaded syllabus" in prompt
        assert "do not invent topics" in prompt.lower() or \
            "Do not guess" in prompt

    def test_personalization_appended(self):
        prompt = build_tutor_system_prompt(
            context="ctx",
            syllabus_selected=True,
            personalization="Student struggles with loops.",
        )
        assert "Student struggles with loops." in prompt

    def test_canonical_not_found_message(self):
        assert "couldn't find that information in the uploaded syllabus" \
            in TUTOR_NOT_FOUND_MESSAGE


# ---------------------------------------------------------------------------
# SyllabusOut.units computed field (chapter -> UI unit mapping)
# ---------------------------------------------------------------------------

def _make_syllabus_out():
    return SyllabusOut(
        id=1,
        title="Intro to Computing",
        status=SyllabusStatus.PARSED,
        subjects=[
            SubjectWithChapters(
                id=10,
                name="Intro to Computing",
                order=0,
                chapters=[
                    ChapterOut(
                        id=100,
                        name="Unit 1: Overview of Computers",
                        description="basics",
                        topics=["Definition", "Characteristics"],
                        order=0,
                        subject_id=10,
                        estimated_hours=3,
                    ),
                    ChapterOut(
                        id=101,
                        name="Unit 2: The Computer System Hardware",
                        order=1,
                        subject_id=10,
                        estimated_hours=0,
                    ),
                ],
            ),
            SubjectWithChapters(
                id=20,
                name="Second Subject",
                order=1,
                chapters=[
                    ChapterOut(
                        id=200,
                        name="Unit 3: Computer Networks",
                        topics=["LAN and WAN"],
                        order=0,
                        subject_id=20,
                        estimated_hours=4,
                    ),
                ],
            ),
        ],
    )


class TestSyllabusOutUnits:
    def test_units_map_to_chapters_not_subjects(self):
        syllabus = _make_syllabus_out()
        units = syllabus.units
        # Two chapters on subject 1 plus one chapter on subject 2 must
        # yield exactly three UI units - NOT two aggregated by subject.
        assert len(units) == 3

    def test_unit_numbers_are_global_running_index(self):
        units = _make_syllabus_out().units
        assert [u.unitNumber for u in units] == [1, 2, 3]

    def test_titles_are_chapter_names_in_document_order(self):
        units = _make_syllabus_out().units
        assert [u.title for u in units] == [
            "Unit 1: Overview of Computers",
            "Unit 2: The Computer System Hardware",
            "Unit 3: Computer Networks",
        ]

    def test_hours_come_from_each_chapter_only(self):
        units = _make_syllabus_out().units
        # Per-chapter hours (0 when the source states none) - no
        # aggregation, no invention.
        assert [u.estimatedHours for u in units] == [3, 0, 4]

    def test_topics_passthrough(self):
        units = _make_syllabus_out().units
        assert units[0].topics == ["Definition", "Characteristics"]
        assert units[2].topics == ["LAN and WAN"]
        # Chapter without topics yields None, not an empty list.
        assert units[1].topics is None

    def test_totals_aggregate_everything(self):
        syllabus = _make_syllabus_out()
        assert syllabus.totalTopics == 3
        assert syllabus.estimatedHours == 7

    def test_subjects_still_exposed_for_other_consumers(self):
        syllabus = _make_syllabus_out()
        assert len(syllabus.subjects) == 2
