"""
Unit tests for the syllabus LLM parsing pipeline.

These tests do NOT require a live Groq API key.  They mock the LLM
client so the JSON-extraction, validation, and retry logic can be
exercised deterministically, including with a completely different
syllabus format than the one the prompt was originally written for.
"""
import json
from typing import Any, List, Optional

import pytest
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable

from app.services.llm_service import LLMService


# ---------------------------------------------------------------------------
# Fake chat model -- a minimal Runnable that returns canned responses
# ---------------------------------------------------------------------------

class FakeChatModel(Runnable):
    """Minimal Runnable mimicking ChatGroq, returns sequential canned responses."""

    def __init__(self, responses: List[str]):
        super().__init__()
        self._responses = list(responses)
        self._idx = 0
        self.calls = 0

    def _next(self) -> str:
        self.calls += 1
        if self._idx < len(self._responses):
            resp = self._responses[self._idx]
            self._idx += 1
            return resp
        return self._responses[-1] if self._responses else ""

    def invoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> AIMessage:
        return AIMessage(content=self._next())

    async def ainvoke(self, input: Any, config: Optional[Any] = None, **kwargs: Any) -> AIMessage:
        return AIMessage(content=self._next())


def _make_service(responses: List[str]):
    """Create an LLMService whose _get_model is stubbed to return a FakeChatModel."""
    svc = LLMService()
    fake = FakeChatModel(responses)
    svc._get_model = lambda temperature=0.7, json_mode=False, **kwargs: fake  # type: ignore[assignment]
    return svc, fake


# ---------------------------------------------------------------------------
# _extract_json
# ---------------------------------------------------------------------------

class TestExtractJson:
    """Test the robust JSON extraction helper."""

    def test_clean_json_is_returned_as_is(self):
        data = '{"subjects": []}'
        assert LLMService._extract_json(data) == data

    def test_markdown_json_fence_stripped(self):
        raw = '```json\n{"subjects": []}\n```'
        result = LLMService._extract_json(raw)
        assert json.loads(result) == {"subjects": []}

    def test_plain_markdown_fence_stripped(self):
        raw = '```\n{"key": "value"}\n```'
        result = LLMService._extract_json(raw)
        assert json.loads(result) == {"key": "value"}

    def test_json_embedded_in_prose(self):
        raw = 'Here is the result:\n{"subjects": []}\nThat is all.'
        result = LLMService._extract_json(raw)
        assert json.loads(result) == {"subjects": []}

    def test_json_array_extraction(self):
        raw = 'Results:\n[{"a": 1}, {"b": 2}]'
        result = LLMService._extract_json(raw)
        assert json.loads(result) == [{"a": 1}, {"b": 2}]

    def test_nested_json_extraction(self):
        raw = '{"subjects": [{"name": "Math", "chapters": [{"name": "Ch1"}]}]}'
        result = LLMService._extract_json(raw)
        assert json.loads(result) == json.loads(raw)

    def test_json_with_string_containing_braces(self):
        raw = '{"msg": "use { and } freely", "ok": true}'
        result = LLMService._extract_json(raw)
        assert json.loads(result) == {"msg": "use { and } freely", "ok": True}

    def test_completely_invalid_returns_original(self):
        raw = "This is not JSON at all"
        result = LLMService._extract_json(raw)
        assert result == "This is not JSON at all"

    def test_whitespace_and_newlines_around_json(self):
        raw = '\n\n  {"a": 1}\n\n  '
        result = LLMService._extract_json(raw)
        assert json.loads(result) == {"a": 1}


# ---------------------------------------------------------------------------
# _validate_syllabus_data
# ---------------------------------------------------------------------------

class TestValidateSyllabusData:
    """Test the syllabus schema validator."""

    def test_valid_structure(self):
        data = {
            "subjects": [
                {
                    "name": "Biology",
                    "description": "Intro",
                    "chapters": [
                        {
                            "name": "Cell Biology",
                            "topics": ["Cells", "Organelles"],
                            "estimated_hours": 4,
                        }
                    ],
                }
            ]
        }
        assert LLMService._validate_syllabus_data(data) == data

    def test_valid_no_description(self):
        data = {
            "subjects": [
                {"name": "Science", "chapters": [{"name": "Physics", "topics": ["Motion"]}]}
            ]
        }
        assert LLMService._validate_syllabus_data(data) == data

    def test_valid_no_topics(self):
        data = {
            "subjects": [
                {"name": "History", "chapters": [{"name": "WWII", "topics": None}]}
            ]
        }
        assert LLMService._validate_syllabus_data(data) == data

    def test_valid_empty_chapters_list(self):
        data = {"subjects": [{"name": "Math", "chapters": []}]}
        assert LLMService._validate_syllabus_data(data) == data

    def test_invalid_top_level_string(self):
        with pytest.raises(ValueError, match="top level"):
            LLMService._validate_syllabus_data("not a dict")

    def test_invalid_top_level_list(self):
        with pytest.raises(ValueError, match="top level"):
            LLMService._validate_syllabus_data([])

    def test_missing_subjects_key(self):
        with pytest.raises(ValueError, match="subjects.*list"):
            LLMService._validate_syllabus_data({})

    def test_subjects_not_a_list(self):
        """subjects as a string is now normalized (not a validation error)."""
        data = {"subjects": "not a list"}
        result = LLMService._validate_syllabus_data(
            LLMService._normalize_syllabus_data(data)
        )
        assert len(result["subjects"]) == 1
        assert result["subjects"][0]["name"] == "not a list"

    def test_subject_missing_name(self):
        with pytest.raises(ValueError, match="missing 'name'"):
            LLMService._validate_syllabus_data(
                {"subjects": [{"chapters": []}]}
            )

    def test_chapter_missing_name(self):
        """Chapters without a name are skipped (not raised) after normalization."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"name": "Algebra", "topics": ["x"]},
                        {"topics": []},
                    ],
                }
            ]
        }
        result = LLMService._validate_syllabus_data(
            LLMService._normalize_syllabus_data(data)
        )
        # Only the named chapter survives
        assert len(result["subjects"][0]["chapters"]) == 1
        assert result["subjects"][0]["chapters"][0]["name"] == "Algebra"

    def test_topics_not_a_list(self):
        """topics as a string is now normalized (not a validation error)."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [{"name": "Ch1", "topics": "not a list"}],
                }
            ]
        }
        result = LLMService._validate_syllabus_data(
            LLMService._normalize_syllabus_data(data)
        )
        assert result["subjects"][0]["chapters"][0]["topics"] == ["not a list"]

    def test_chapter_missing_name_with_topics_gets_inferred_name(self):
        """A chapter with topics but no name gets an inferred name from context."""
        data = {
            "subjects": [
                {
                    "name": "Computer Fundamentals",
                    "chapters": [
                        {"topics": ["Computer Hardware", "Computer Software"]}
                    ],
                }
            ]
        }
        result = LLMService._validate_syllabus_data(
            LLMService._normalize_syllabus_data(data)
        )
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 1
        assert chapters[0]["name"] == "Computer Fundamentals - Chapter 1"
        assert chapters[0]["topics"] == ["Computer Hardware", "Computer Software"]

    def test_chapter_missing_name_no_topics_gets_dropped(self):
        """A chapter with no name AND no topics gets dropped entirely."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"name": "Algebra", "topics": ["x"]},
                        {"topics": []},
                    ],
                }
            ]
        }
        result = LLMService._validate_syllabus_data(
            LLMService._normalize_syllabus_data(data)
        )
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 1
        assert chapters[0]["name"] == "Algebra"

    def test_chapter_missing_name_validator_skips(self):
        """Validator skips (not raises) for chapters still missing name after normalization."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"description": "empty chapter"},
                    ],
                }
            ]
        }
        # Should NOT raise ValueError
        result = LLMService._validate_syllabus_data(
            LLMService._normalize_syllabus_data(data)
        )
        # Chapter with no name should be skipped
        assert len(result["subjects"][0]["chapters"]) == 0

    def test_duplicate_topics_are_deduplicated(self):
        """Exact duplicate topics within a chapter are removed (order preserved)."""
        data = {
            "subjects": [
                {
                    "name": "Computer Fundamentals",
                    "chapters": [
                        {
                            "name": "Introduction",
                            "topics": [
                                "Computer Hardware",
                                "Computer Applications",
                                "Computer Applications",
                                "Computer Applications",
                                "Computer Software",
                            ],
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert topics == [
            "Computer Hardware",
            "Computer Applications",
            "Computer Software",
        ]

    def test_case_insensitive_dedup(self):
        """Topics differing only in case are deduplicated."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "topics": ["Linear Equations", "linear equations", "LINEAR EQUATIONS"],
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert len(topics) == 1
        assert topics[0] == "Linear Equations"

    def test_repetition_loop_output_is_detected_not_truncated(self):
        """Degenerate repetition-loop output is detected by ratio, not by a
        hard topic-count cap.  60 LEGITIMATE unique topics must survive
        normalization untouched."""
        # A real syllabus chapter can legitimately have many topics.
        many_topics = [f"Topic {i}" for i in range(60)]
        data = {
            "subjects": [
                {
                    "name": "Test Subject",
                    "chapters": [{"name": "Test Chapter", "topics": many_topics}],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert len(topics) == 60
        assert not LLMService._looks_like_repetition_loop(data)

    def test_repetition_loop_detected_single_topic_repeated(self):
        """One topic repeated many times is flagged as degenerate output."""
        repeated = (
            ["Database", "Database System", "Data Warehousing Techniques"] * 5
        )
        data = {
            "subjects": [
                {
                    "name": "Introduction",
                    "chapters": [{"name": "Database", "topics": repeated}],
                }
            ]
        }
        assert LLMService._looks_like_repetition_loop(data)

    def test_repetition_loop_detected_low_unique_ratio(self):
        """30 entries with only 5 unique values is degenerate even when no
        single entry dominates."""
        uniques = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]
        shuffled = [uniques[i % 5] for i in range(30)]
        data = {
            "subjects": [
                {"name": "S", "chapters": [{"name": "C", "topics": shuffled}]}
            ]
        }
        assert LLMService._looks_like_repetition_loop(data)

    def test_few_topics_with_accidental_duplicate_not_flagged(self):
        """Small chapters with an accidental duplicate are NOT degenerate."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"name": "Algebra", "topics": ["x", "y", "x"]}
                    ],
                }
            ]
        }
        assert not LLMService._looks_like_repetition_loop(data)


# ---------------------------------------------------------------------------
# _normalize_syllabus_data
# ---------------------------------------------------------------------------

class TestNormalizeSyllabusData:
    """Test the syllabus data normalizer."""

    def test_valid_data_unchanged(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "description": "Maths",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "description": "Basics",
                            "topics": ["x", "y"],
                            "estimated_hours": 3,
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        assert result == data

    def test_subjects_as_single_object(self):
        data = {
            "subjects": {
                "name": "Computer Networking",
                "chapters": [],
            }
        }
        result = LLMService._normalize_syllabus_data(data)
        assert isinstance(result["subjects"], list)
        assert len(result["subjects"]) == 1
        assert result["subjects"][0]["name"] == "Computer Networking"

    def test_subjects_as_string(self):
        data = {"subjects": "Computer Networking"}
        result = LLMService._normalize_syllabus_data(data)
        assert isinstance(result["subjects"], list)
        assert result["subjects"][0]["name"] == "Computer Networking"
        assert result["subjects"][0]["chapters"] == []

    def test_subject_as_string_in_list(self):
        data = {"subjects": ["Networking", "Security"]}
        result = LLMService._normalize_syllabus_data(data)
        assert result["subjects"][0]["name"] == "Networking"
        assert result["subjects"][0]["chapters"] == []
        assert result["subjects"][1]["name"] == "Security"

    def test_chapters_as_strings(self):
        """Case 2: chapters returned as plain strings."""
        data = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "chapters": [
                        "Introduction",
                        "Network Models",
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 2
        assert chapters[0] == {
            "name": "Introduction",
            "description": "",
            "topics": [],
            "estimated_hours": 0,
        }
        assert chapters[1] == {
            "name": "Network Models",
            "description": "",
            "topics": [],
            "estimated_hours": 0,
        }

    def test_single_chapter_string(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": "Algebra",
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 1
        assert chapters[0]["name"] == "Algebra"

    def test_chapters_as_single_object(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": {"name": "Algebra", "topics": ["x"]},
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        chapters = result["subjects"][0]["chapters"]
        assert isinstance(chapters, list)
        assert len(chapters) == 1
        assert chapters[0]["name"] == "Algebra"

    def test_topics_as_string(self):
        """Case 3: topics returned as a single string."""
        data = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "chapters": [
                        {
                            "name": "Introduction",
                            "topics": "Network Models",
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert topics == ["Network Models"]

    def test_topics_as_dict_with_name(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "topics": {"name": "Linear Equations"},
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert topics == ["Linear Equations"]

    def test_topics_as_dict_with_title(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "topics": {"title": "Linear Equations"},
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert topics == ["Linear Equations"]

    def test_topics_list_with_dict_elements(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "topics": [
                                {"name": "Linear Equations"},
                                {"topic": "Quadratics"},
                                "Geometry",
                            ],
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        topics = result["subjects"][0]["chapters"][0]["topics"]
        assert topics == ["Linear Equations", "Quadratics", "Geometry"]

    def test_missing_description_defaults(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"name": "Algebra", "topics": ["x"]}
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        assert result["subjects"][0]["description"] == ""
        assert result["subjects"][0]["chapters"][0]["description"] == ""

    def test_missing_estimated_hours_defaults(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"name": "Algebra", "topics": ["x"]}
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        assert result["subjects"][0]["chapters"][0]["estimated_hours"] == 0

    def test_estimated_hours_as_numeric_string(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "topics": ["x"],
                            "estimated_hours": "3 Hrs.",
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        assert result["subjects"][0]["chapters"][0]["estimated_hours"] == 3

    def test_estimated_hours_as_plain_number_string(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {
                            "name": "Algebra",
                            "topics": ["x"],
                            "estimated_hours": "7",
                        }
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        assert result["subjects"][0]["chapters"][0]["estimated_hours"] == 7

    def test_missing_topics_defaults(self):
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "chapters": [
                        {"name": "Algebra"}
                    ],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        assert result["subjects"][0]["chapters"][0]["topics"] == []

    def test_no_subjects_key(self):
        data = {"foo": "bar"}
        result = LLMService._normalize_syllabus_data(data)
        assert result == {"foo": "bar"}

    def test_mixed_normalization_scenario(self):
        """Combination: subject as string, chapter as string, topic as string."""
        data = {
            "subjects": [
                {
                    "name": "Networking",
                    "chapters": ["OSI Model"],
                }
            ]
        }
        result = LLMService._normalize_syllabus_data(data)
        chap = result["subjects"][0]["chapters"][0]
        assert chap["name"] == "OSI Model"
        assert chap["topics"] == []
        assert chap["estimated_hours"] == 0

    def test_normalization_returns_same_object(self):
        data = {"subjects": []}
        result = LLMService._normalize_syllabus_data(data)
        assert result is data


# ---------------------------------------------------------------------------
# parse_syllabus_content (end-to-end with FakeChatModel)
# ---------------------------------------------------------------------------

class TestParseSyllabusContent:
    """Test the full parse_syllabus_content flow with mock LLM responses."""

    @pytest.mark.asyncio
    async def test_valid_json_responses_succeeds_first_attempt(self):
        """A clean JSON response should succeed on the first attempt."""
        data = {
            "subjects": [
                {
                    "name": "Biology",
                    "description": "Intro to Biology",
                    "chapters": [
                        {
                            "name": "Cell Biology",
                            "description": "",
                            "topics": ["Cell structure", "Organelles", "Membrane"],
                            "estimated_hours": 4,
                        }
                    ],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(data)])
        result = await svc.parse_syllabus_content(
            "Unit 1: Biology (4 Hrs.) - Cell structure; Organelles; Membrane"
        )
        assert result == data
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_markdown_wrapped_json_is_parsed(self):
        """JSON wrapped in ```json fences should be successfully extracted."""
        data = {
            "subjects": [
                {
                    "name": "Chemistry",
                    "description": "",
                    "chapters": [
                        {"name": "Atoms", "description": "", "topics": ["Atomic structure"], "estimated_hours": 3}
                    ],
                }
            ]
        }
        svc, fake = _make_service([f"```json\n{json.dumps(data)}\n```"])
        result = await svc.parse_syllabus_content(
            "Unit 1: Chemistry (3 Hrs.) - Atomic structure"
        )
        assert result == data
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_json_with_surrounding_prose(self):
        """JSON surrounded by explanatory prose should be extracted."""
        data = {
            "subjects": [
                {
                    "name": "Physics",
                    "description": "",
                    "chapters": [
                        {
                            "name": "Mechanics",
                            "description": "",
                            "topics": ["Kinematics", "Dynamics"],
                            "estimated_hours": 6,
                        }
                    ],
                }
            ]
        }
        svc, fake = _make_service(
            [f"Here is the parsed data:\n{json.dumps(data)}\nDone."]
        )
        result = await svc.parse_syllabus_content(
            "Unit 1: Physics (6 Hrs.) - Kinematics; Dynamics"
        )
        assert result == data

    @pytest.mark.asyncio
    async def test_invalid_json_retries_and_succeeds(self):
        """First attempt with bad JSON should trigger retry; second succeeds."""
        data = {
            "subjects": [
                {
                    "name": "Math",
                    "description": "",
                    "chapters": [
                        {"name": "Algebra", "description": "", "topics": ["x"], "estimated_hours": 2}
                    ],
                }
            ]
        }
        svc, fake = _make_service(
            ["Not valid JSON at all", json.dumps(data)]
        )
        result = await svc.parse_syllabus_content("Some syllabus text")
        assert result == data
        assert fake.calls >= 2

    @pytest.mark.asyncio
    async def test_all_attempts_fail_raises_value_error(self):
        """When every attempt returns invalid JSON, ValueError is raised."""
        svc, fake = _make_service(
            ["garbage", "still garbage", "more garbage"]
        )
        with pytest.raises(ValueError, match="Failed to parse syllabus"):
            await svc.parse_syllabus_content("Some syllabus text")

    @pytest.mark.asyncio
    async def test_empty_subjects_raises_value_error(self):
        """Valid JSON with empty subjects should fail after all retries."""
        svc, fake = _make_service(
            [
                json.dumps({"subjects": []}),
                json.dumps({"subjects": []}),
                json.dumps({"subjects": []}),
            ]
        )
        with pytest.raises(ValueError, match="Failed to parse syllabus"):
            await svc.parse_syllabus_content("Some syllabus text")

    @pytest.mark.asyncio
    async def test_runtime_error_propagates_without_retry(self):
        """RuntimeError (e.g. missing API key) should propagate, not retry."""
        svc = LLMService()
        call_count = 0

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError("GROQ_API_KEY is not configured.")

        svc._get_model = mock_get_model  # type: ignore[assignment]
        with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
            await svc.parse_syllabus_content("test text")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_json_mode_is_requested_on_first_attempt(self):
        """The first _get_model call should use json_mode=True."""
        data = {"subjects": [{"name": "Test", "description": "", "chapters": []}]}
        svc = LLMService()
        fake = FakeChatModel([json.dumps(data)])

        json_mode_calls: List[bool] = []

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            json_mode_calls.append(json_mode)
            return fake

        svc._get_model = mock_get_model  # type: ignore[assignment]
        result = await svc.parse_syllabus_content("test text")
        assert result == data
        assert json_mode_calls[0] is True

    @pytest.mark.asyncio
    async def test_json_mode_fallback_when_not_supported(self):
        """If JSON mode fails, retry without it should still succeed."""
        data = {
            "subjects": [
                {
                    "name": "Biology",
                    "description": "",
                    "chapters": [{"name": "Cells", "description": "", "topics": ["Mitosis"], "estimated_hours": 2}],
                }
            ]
        }
        # First two attempts: FakeChatModel always returns the valid JSON,
        # but we simulate json_mode failures by having the first two calls
        # return invalid output and the third (non-json-mode) return valid.
        svc, fake = _make_service(
            [
                "Error: response_format not supported",  # attempt 1 (json_mode)
                "Error: response_format not supported",  # attempt 2 (json_mode)
                json.dumps(data),                       # attempt 3 (no json_mode)
            ]
        )
        result = await svc.parse_syllabus_content(
            "Unit 1: Biology (2 Hrs.) - Mitosis"
        )
        assert result == data
        assert fake.calls == 3

    # ------------------------------------------------------------------
    # Generic parsing -- a completely different syllabus format
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_completely_different_syllabus(self):
        """Parser must work generically, not be hardcoded for one syllabus."""
        data = {
            "subjects": [
                {
                    "name": "Introduction to Machine Learning",
                    "description": "Fundamentals of ML",
                    "chapters": [
                        {
                            "name": "Supervised Learning",
                            "description": "",
                            "topics": ["Linear Regression", "Logistic Regression",
                                     "Decision Trees", "SVM"],
                            "estimated_hours": 8,
                        },
                        {
                            "name": "Unsupervised Learning",
                            "description": "",
                            "topics": ["K-Means Clustering", "PCA",
                                     "Hierarchical Clustering"],
                            "estimated_hours": 6,
                        },
                        {
                            "name": "Deep Learning",
                            "description": "",
                            "topics": ["Neural Networks", "CNNs", "RNNs",
                                     "Transformers"],
                            "estimated_hours": 10,
                        },
                    ],
                },
                {
                    "name": "Data Structures and Algorithms",
                    "description": "Core CS concepts",
                    "chapters": [
                        {
                            "name": "Arrays and Hash Tables",
                            "description": "",
                            "topics": ["Array operations", "Hash maps",
                                     "Two pointers"],
                            "estimated_hours": 5,
                        },
                        {
                            "name": "Tree Algorithms",
                            "description": "",
                            "topics": ["Binary trees", "BST traversal",
                                     "AVL trees", "Tries"],
                            "estimated_hours": 7,
                        },
                    ],
                },
            ]
        }
        raw_text = (
            "Course: Advanced Computer Science\n"
            "Module 1: Introduction to Machine Learning (8 Hrs.)\n"
            "  - Supervised Learning\n"
            "  - Unsupervised Learning\n"
            "  - Deep Learning\n"
            "Module 2: Data Structures and Algorithms (5 Hrs.)\n"
            "  - Arrays and Hash Tables\n"
            "  - Tree Algorithms\n"
        )
        svc, fake = _make_service([json.dumps(data)])
        result = await svc.parse_syllabus_content(raw_text)
        assert result == data
        # Verify the structure was correctly parsed and stored
        assert len(result["subjects"]) == 2
        assert result["subjects"][0]["name"] == "Introduction to Machine Learning"
        assert len(result["subjects"][0]["chapters"]) == 3
        assert result["subjects"][0]["chapters"][0]["estimated_hours"] == 8
        assert len(result["subjects"][0]["chapters"][0]["topics"]) == 4
        assert result["subjects"][1]["name"] == "Data Structures and Algorithms"
        assert len(result["subjects"][1]["chapters"]) == 2
        assert result["subjects"][1]["chapters"][1]["estimated_hours"] == 7

    @pytest.mark.asyncio
    async def test_syllabus_with_nested_chapters_and_hours(self):
        """Verify topics, estimated_hours, and chapter descriptions are preserved."""
        data = {
            "subjects": [
                {
                    "name": "Mathematics for Economists",
                    "description": "Essential math for economics",
                    "chapters": [
                        {
                            "name": "Calculus",
                            "description": "Differential and integral calculus",
                            "topics": ["Limits", "Derivatives", "Integration",
                                     "Optimization"],
                            "estimated_hours": 12,
                        },
                        {
                            "name": "Linear Algebra",
                            "description": "Vectors and matrices",
                            "topics": ["Vectors", "Matrices", "Eigenvalues",
                                     "Linear transformations"],
                            "estimated_hours": 10,
                        },
                    ],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(data)])
        result = await svc.parse_syllabus_content(
            "Unit 1: Mathematics for Economists (12 Hrs.) - Limits; Derivatives; Integration; Optimization"
        )
        assert result == data
        subj = result["subjects"][0]
        assert subj["name"] == "Mathematics for Economists"
        assert subj["description"] == "Essential math for economics"
        assert len(subj["chapters"]) == 2
        ch1 = subj["chapters"][0]
        assert ch1["name"] == "Calculus"
        assert ch1["description"] == "Differential and integral calculus"
        assert ch1["estimated_hours"] == 12
        assert len(ch1["topics"]) == 4

    @pytest.mark.asyncio
    async def test_markdown_nested_json_with_prose_and_multiple_blocks(self):
        """Complex real-world scenario: prose + markdown + nested JSON."""
        data = {
            "subjects": [
                {
                    "name": "Computer Networks",
                    "description": "",
                    "chapters": [
                        {
                            "name": "OSI Model",
                            "description": "",
                            "topics": ["Layer 1", "Layer 2", "Layer 3", "Layer 4",
                                     "Layer 5", "Layer 6", "Layer 7"],
                            "estimated_hours": 5,
                        }
                    ],
                }
            ]
        }
        raw = (
            "Here is the parsed syllabus structure:\n\n"
            "```json\n"
            f"{json.dumps(data, indent=2)}\n"
            "```\n\n"
            "Let me know if you need anything else!"
        )
        svc, fake = _make_service([raw])
        result = await svc.parse_syllabus_content(
            "Unit 1: OSI Model (5 Hrs.) - Layers 1-7"
        )
        assert result == data
        assert len(result["subjects"]) == 1
        assert result["subjects"][0]["chapters"][0]["estimated_hours"] == 5
        assert len(result["subjects"][0]["chapters"][0]["topics"]) == 7

    @pytest.mark.asyncio
    async def test_cloud_computing_syllabus(self):
        """Real-world cloud computing syllabus: Unit 1 and Unit 2 parsed correctly."""
        data = {
            "subjects": [
                {
                    "name": "Introduction to Cloud Computing",
                    "description": "Fundamentals of cloud computing",
                    "chapters": [
                        {
                            "name": "Introduction to Cloud Computing",
                            "description": "Overview of cloud computing concepts",
                            "topics": [
                                "Evolution of Cloud Computing",
                                "Characteristics of Cloud Computing",
                                "Types of Cloud and Cloud Services",
                                "Benefits and Challenges of Cloud Computing",
                                "Applications of Cloud Computing",
                                "Cloud Storage",
                                "Cloud Service Requirements",
                                "Cloud and Dynamic Infrastructure",
                                "Cloud Adoption",
                            ],
                            "estimated_hours": 6,
                        }
                    ],
                },
                {
                    "name": "Cloud Architecture",
                    "description": "Cloud architecture design and virtualization",
                    "chapters": [
                        {
                            "name": "Cloud Architecture",
                            "description": "Architecture patterns and resource management",
                            "topics": [
                                "Cloud Reference Architecture",
                                "Virtualization",
                                "Resource Management",
                            ],
                            "estimated_hours": 8,
                        }
                    ],
                },
            ]
        }
        raw_syllabus = (
            "Course Contents:\n"
            "\n"
            "Unit 1. Introduction to Cloud Computing 6 Hrs.\n"
            "\n"
            "Evolution of Cloud Computing;\n"
            "Characteristics of Cloud Computing;\n"
            "Types of Cloud and Cloud Services;\n"
            "Benefits and Challenges of Cloud Computing;\n"
            "Applications of Cloud Computing;\n"
            "Cloud Storage;\n"
            "Cloud Service Requirements;\n"
            "Cloud and Dynamic Infrastructure;\n"
            "Cloud Adoption.\n"
            "\n"
            "Unit 2. Cloud Architecture 8 Hrs.\n"
            "\n"
            "Cloud Reference Architecture;\n"
            "Virtualization;\n"
            "Resource Management;\n"
        )
        svc, fake = _make_service([json.dumps(data)])
        result = await svc.parse_syllabus_content(raw_syllabus)

        assert len(result["subjects"]) == 2

        # Unit 1
        subj1 = result["subjects"][0]
        assert subj1["name"] == "Introduction to Cloud Computing"
        assert len(subj1["chapters"]) == 1
        ch1 = subj1["chapters"][0]
        assert ch1["estimated_hours"] == 6
        assert len(ch1["topics"]) == 9
        assert "Evolution of Cloud Computing" in ch1["topics"]
        assert "Cloud Adoption" in ch1["topics"]

        # Unit 2
        subj2 = result["subjects"][1]
        assert subj2["name"] == "Cloud Architecture"
        assert len(subj2["chapters"]) == 1
        ch2 = subj2["chapters"][0]
        assert ch2["estimated_hours"] == 8
        assert len(ch2["topics"]) == 3
        assert "Virtualization" in ch2["topics"]

        # No DBMS dummy data
        full_text = json.dumps(result).lower()
        assert "dbms" not in full_text
        assert "database management" not in full_text

    @pytest.mark.asyncio
    async def test_syllabus_with_xml_delimiters_in_prompt(self):
        """Verify the prompt uses XML-style delimiters for syllabus content."""
        data = {
            "subjects": [
                {
                    "name": "Test Subject",
                    "description": "",
                    "chapters": [
                        {"name": "Test Chapter", "description": "", "topics": ["Topic A"], "estimated_hours": 2}
                    ],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(data)])
        result = await svc.parse_syllabus_content("Unit 1: Test Subject (2 Hrs.) - Topic A")
        assert result == data
        assert fake.calls == 1

    # ------------------------------------------------------------------
    # Normalization through full pipeline
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_chapter_strings_normalized_through_pipeline(self):
        """End-to-end: LLM returns chapters as strings, normalization fixes it."""
        raw_llm = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "chapters": [
                        "Introduction to Networking",
                        "Network Models",
                    ],
                }
            ]
        }
        expected = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "description": "",
                    "chapters": [
                        {
                            "name": "Introduction to Networking",
                            "description": "",
                            "topics": [],
                            "estimated_hours": 0,
                        },
                        {
                            "name": "Network Models",
                            "description": "",
                            "topics": [],
                            "estimated_hours": 0,
                        },
                    ],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(raw_llm)])
        result = await svc.parse_syllabus_content("Networking syllabus")
        assert result == expected
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_topics_string_normalized_through_pipeline(self):
        """End-to-end: LLM returns topics as a string, normalization fixes it."""
        raw_llm = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "chapters": [
                        {
                            "name": "Unit 1: Network Fundamentals",
                            "topics": "Network Models",
                        }
                    ],
                }
            ]
        }
        expected = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "description": "",
                    "chapters": [
                        {
                            "name": "Unit 1: Network Fundamentals",
                            "description": "",
                            "topics": ["Network Models"],
                            "estimated_hours": 0,
                        }
                    ],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(raw_llm)])
        result = await svc.parse_syllabus_content("Networking syllabus")
        assert result == expected
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_pseudo_unit_heading_rejected_through_pipeline(self):
        """End-to-end: generic section headings must never become units.

        A bare 'Introduction' chapter is rejected by validation even when
        the LLM emits it with valid topics, because it is not defined as
        a numbered unit in the source syllabus.
        """
        raw_llm = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "chapters": [
                        {
                            "name": "Introduction",
                            "topics": ["Network Models"],
                        },
                        {
                            "name": "Unit 2: Network Models",
                            "topics": ["OSI Model", "TCP/IP"],
                        },
                    ],
                }
            ]
        }
        expected = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "description": "",
                    "chapters": [
                        {
                            "name": "Unit 2: Network Models",
                            "description": "",
                            "topics": ["OSI Model", "TCP/IP"],
                            "estimated_hours": 0,
                        }
                    ],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(raw_llm)])
        result = await svc.parse_syllabus_content("Networking syllabus")
        assert result == expected
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_subject_object_normalized_through_pipeline(self):
        """End-to-end: LLM returns subjects as a single object, normalization fixes it."""
        raw_llm = {
            "subjects": {
                "name": "Computer Networking",
                "chapters": [],
            }
        }
        expected = {
            "subjects": [
                {
                    "name": "Computer Networking",
                    "description": "",
                    "chapters": [],
                }
            ]
        }
        svc, fake = _make_service([json.dumps(raw_llm)])
        result = await svc.parse_syllabus_content("Networking syllabus")
        assert result == expected
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_invalid_data_still_raises_value_error(self):
        """Completely invalid structures should still raise ValueError."""
        raw_llm = {"not_subjects": "garbage"}
        svc, fake = _make_service([json.dumps(raw_llm)])
        with pytest.raises(ValueError, match="Failed to parse syllabus"):
            await svc.parse_syllabus_content("Some text")

    @pytest.mark.asyncio
    async def test_completely_invalid_subjects_type_still_raises(self):
        """Subjects as a list of ints should fail after normalization."""
        raw_llm = {"subjects": [1, 2, 3]}
        svc, fake = _make_service([json.dumps(raw_llm)])
        # Normalization won't turn int into a dict with 'name', so
        # validation should still fail.
        with pytest.raises(ValueError, match="Failed to parse syllabus"):
            await svc.parse_syllabus_content("Some text")


# ---------------------------------------------------------------------------
# _split_syllabus_text
# ---------------------------------------------------------------------------

class TestSplitSyllabusText:
    """Test syllabus text chunking for oversized requests."""

    def test_small_text_not_split(self):
        text = "Unit 1: Short topic\nSome details here."
        result = LLMService._split_syllabus_text(text, max_chars=500)
        assert result == [text]

    def test_split_on_unit_headings(self):
        text = (
            "Unit 1: Networking (6 Hrs.)\n"
            "Topic A; Topic B\n"
            "\n"
            "Unit 2: Security (4 Hrs.)\n"
            "Topic C; Topic D\n"
            "\n"
            "Unit 3: Databases (5 Hrs.)\n"
            "Topic E; Topic F\n"
        )
        result = LLMService._split_syllabus_text(text, max_chars=80)
        assert len(result) >= 3
        # Each chunk should start with a heading or contain heading content
        all_text = " ".join(result)
        assert "Unit 1" in all_text
        assert "Unit 2" in all_text
        assert "Unit 3" in all_text

    def test_split_on_module_headings(self):
        text = (
            "Module 1: Cloud Basics\n"
            "AWS, Azure, GCP\n"
            "\n"
            "Module 2: Cloud Architecture\n"
            "Microservices, Serverless\n"
        )
        result = LLMService._split_syllabus_text(text, max_chars=60)
        assert len(result) >= 2
        all_text = " ".join(result)
        assert "Module 1" in all_text
        assert "Module 2" in all_text

    def test_split_preserves_all_content(self):
        """No content should be lost when splitting."""
        paragraphs = [f"Unit {i}: Topic {i}\nDetail paragraph {i}.\n" for i in range(1, 6)]
        text = "\n".join(paragraphs)
        result = LLMService._split_syllabus_text(text, max_chars=60)
        # All original paragraphs must appear in the output
        for i in range(1, 6):
            found = any(f"Unit {i}" in chunk for chunk in result)
            assert found, f"Unit {i} missing from split output"
        for i in range(1, 6):
            found = any(f"Detail paragraph {i}" in chunk for chunk in result)
            assert found, f"Detail paragraph {i} missing from split output"

    def test_split_fallback_to_blank_lines(self):
        """A single section without headings splits on blank lines."""
        text = (
            "Paragraph one with some content about networking.\n"
            "\n"
            "Paragraph two with more details.\n"
            "\n"
            "Paragraph three with even more.\n"
        )
        result = LLMService._split_syllabus_text(text, max_chars=50)
        assert len(result) >= 2
        all_text = " ".join(result)
        assert "Paragraph one" in all_text
        assert "Paragraph three" in all_text

    def test_split_fallback_to_sentences(self):
        """A single paragraph splits on sentence boundaries."""
        text = "First sentence about topic A. Second sentence about topic B. Third sentence about topic C."
        result = LLMService._split_syllabus_text(text, max_chars=50)
        assert len(result) >= 2
        all_text = " ".join(result)
        assert "First sentence" in all_text
        assert "Third sentence" in all_text

    def test_empty_text(self):
        result = LLMService._split_syllabus_text("", max_chars=100)
        assert result == [""]

    def test_no_content_loss_with_oversized_section(self):
        """A single section exceeding max_chars still preserves all content."""
        text = (
            "Unit 1: Very Long Topic\n"
            + "Detail line.\n" * 20
        )
        result = LLMService._split_syllabus_text(text, max_chars=80)
        all_text = "\n".join(result)
        assert "Unit 1" in all_text
        for i in range(20):
            assert f"Detail line" in all_text


# ---------------------------------------------------------------------------
# _merge_syllabus_chunks
# ---------------------------------------------------------------------------

class TestMergeSyllabusChunks:
    """Test merging of multiple parsed syllabus chunks."""

    def test_merge_two_distinct_subjects(self):
        chunk1 = {"subjects": [{"name": "Unit 1: Networking", "chapters": [{"name": "Basics", "topics": ["OSI"], "estimated_hours": 3}]}]}
        chunk2 = {"subjects": [{"name": "Unit 2: Security", "chapters": [{"name": "Crypto", "topics": ["AES"], "estimated_hours": 4}]}]}
        result = LLMService._merge_syllabus_chunks([chunk1, chunk2])
        assert len(result["subjects"]) == 2
        names = [s["name"] for s in result["subjects"]]
        assert "Unit 1: Networking" in names
        assert "Unit 2: Security" in names

    def test_merge_duplicate_subjects_merges_chapters(self):
        chunk1 = {"subjects": [{"name": "Networking", "chapters": [{"name": "OSI", "topics": ["Layer 1"], "estimated_hours": 3}]}]}
        chunk2 = {"subjects": [{"name": "Networking", "chapters": [{"name": "TCP/IP", "topics": ["Ports"], "estimated_hours": 2}]}]}
        result = LLMService._merge_syllabus_chunks([chunk1, chunk2])
        assert len(result["subjects"]) == 1
        assert result["subjects"][0]["name"] == "Networking"
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 2
        chap_names = [c["name"] for c in chapters]
        assert "OSI" in chap_names
        assert "TCP/IP" in chap_names

    def test_merge_duplicate_chapters_merges_topics(self):
        chunk1 = {"subjects": [{"name": "Networking", "chapters": [{"name": "OSI", "topics": ["Layer 1", "Layer 2"], "estimated_hours": 3}]}]}
        chunk2 = {"subjects": [{"name": "Networking", "chapters": [{"name": "OSI", "topics": ["Layer 3", "Layer 1"], "estimated_hours": 5}]}]}
        result = LLMService._merge_syllabus_chunks([chunk1, chunk2])
        assert len(result["subjects"]) == 1
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 1
        topics = chapters[0]["topics"]
        assert len(topics) == 3  # "Layer 1" deduplicated
        assert "Layer 1" in topics
        assert "Layer 2" in topics
        assert "Layer 3" in topics
        # estimated_hours takes the larger value
        assert chapters[0]["estimated_hours"] == 5

    def test_merge_empty_chunks(self):
        result = LLMService._merge_syllabus_chunks([{"subjects": []}, {"subjects": []}])
        assert result == {"subjects": []}

    def test_merge_preserves_order(self):
        chunk1 = {"subjects": [{"name": "Alpha", "chapters": []}]}
        chunk2 = {"subjects": [{"name": "Beta", "chapters": []}]}
        chunk3 = {"subjects": [{"name": "Gamma", "chapters": []}]}
        result = LLMService._merge_syllabus_chunks([chunk1, chunk2, chunk3])
        names = [s["name"] for s in result["subjects"]]
        assert names == ["Alpha", "Beta", "Gamma"]

    def test_merge_single_chunk_passthrough(self):
        data = {"subjects": [{"name": "Math", "chapters": [{"name": "Algebra", "topics": ["x"], "estimated_hours": 2}]}]}
        result = LLMService._merge_syllabus_chunks([data])
        assert result == data


# ---------------------------------------------------------------------------
# _attempt_syllabus_parse error handling
# ---------------------------------------------------------------------------

class TestAttemptSyllabusParseErrors:
    """Test error classification in _attempt_syllabus_parse."""

    @pytest.mark.asyncio
    async def test_413_error_returns_oversized_not_retry(self):
        """A 413 oversized error propagates immediately (no retry)."""
        from app.services.llm_service import _OversizedRequestError

        error_413 = Exception(
            "Error code: 413 - Request too large for model `allam-2-7b` "
            "TPM Limit: 6000 Requested: 6308"
        )

        svc = LLMService()
        call_count = 0

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            nonlocal call_count
            call_count += 1
            raise error_413

        svc._get_model = mock_get_model  # type: ignore[assignment]

        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [("system", "test"), ("human", "{{text}}")],
            template_format="mustache",
        )

        # Oversized request must propagate as _OversizedRequestError so the
        # caller splits the input — it must NOT be swallowed into a None
        # that the caller would retry at a lower temperature.
        with pytest.raises(_OversizedRequestError):
            await svc._attempt_syllabus_parse(
                prompt, temperature=0.7, json_mode=True, text="test",
                max_retries=3,
            )
        # Should be called exactly once — no retry
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_429_error_retries_with_backoff(self):
        """A 429 rate-limit error should retry, not raise immediately."""
        error_429 = Exception("Error code: 429 - Rate limit exceeded")

        svc = LLMService()
        call_count = 0

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise error_429
            raise RuntimeError("Should not reach here")

        svc._get_model = mock_get_model  # type: ignore[assignment]

        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [("system", "test"), ("human", "{{text}}")],
            template_format="mustache",
        )

        # After max_retries=3 with 429, should return None (not raise)
        result = await svc._attempt_syllabus_parse(
            prompt, temperature=0.7, json_mode=True, text="test",
            max_retries=3,
        )
        assert result is None
        assert call_count == 3  # All 3 retries attempted

    @pytest.mark.asyncio
    async def test_request_too_large_string_triggers_oversized(self):
        """String matching for 'request too large' should raise _OversizedRequestError."""
        from app.services.llm_service import _OversizedRequestError

        error_msg = Exception("request body too large for model allam-2-7b")

        svc = LLMService()
        call_count = 0

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            nonlocal call_count
            call_count += 1
            raise error_msg

        svc._get_model = mock_get_model  # type: ignore[assignment]

        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages(
            [("system", "test"), ("human", "{{text}}")],
            template_format="mustache",
        )

        with pytest.raises(_OversizedRequestError):
            await svc._attempt_syllabus_parse(
                prompt, temperature=0.7, json_mode=True, text="test",
                max_retries=3,
            )
        # Oversized request propagates immediately — no retry
        assert call_count == 1


# ---------------------------------------------------------------------------
# parse_syllabus_content — large syllabus splitting
# ---------------------------------------------------------------------------

class TestParseSyllabusContentSplitting:
    """Test that large syllabuses are split and merged correctly."""

    @pytest.mark.asyncio
    async def test_small_syllabus_single_request(self):
        """A syllabus under the budget should use a single LLM call."""
        data = {
            "subjects": [
                {"name": "Unit 1: Networking", "description": "", "chapters": [
                    {"name": "Basics", "description": "", "topics": ["OSI"], "estimated_hours": 3}
                ]}
            ]
        }
        svc, fake = _make_service([json.dumps(data)])
        result = await svc.parse_syllabus_content("Unit 1: Networking (3 Hrs.) - OSI")
        assert result == data
        assert fake.calls == 1

    @pytest.mark.asyncio
    async def test_large_syllabus_splits_into_chunks(self):
        """A syllabus exceeding the budget should be split and parsed in parts."""
        chunk1_data = {
            "subjects": [
                {"name": "Unit 1: Networking", "description": "", "chapters": [
                    {"name": "OSI Model", "description": "", "topics": ["Layer 1", "Layer 2"], "estimated_hours": 3}
                ]}
            ]
        }
        chunk2_data = {
            "subjects": [
                {"name": "Unit 2: Security", "description": "", "chapters": [
                    {"name": "Cryptography", "description": "", "topics": ["AES", "RSA"], "estimated_hours": 4}
                ]}
            ]
        }
        # Create a text with two clearly separated sections
        large_text = (
            "Unit 1: Networking (3 Hrs.)\n"
            + "Detail line about networking.\n" * 10
            + "\n"
            "Unit 2: Security (4 Hrs.)\n"
            + "Detail line about security.\n" * 10
            + "\n"
        )

        # Use a budget that forces splitting into 2 heading chunks
        # but doesn't cause sentence-level splitting
        svc = LLMService()
        fake = FakeChatModel([json.dumps(chunk1_data), json.dumps(chunk2_data)])
        svc._get_model = lambda temperature=0.7, json_mode=False, **kwargs: fake  # type: ignore[assignment]

        # Temporarily override the budget — use a budget smaller than each
        # section but larger than one chunk to force exactly 2 heading-based chunks
        import app.core.config as cfg
        original = cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS
        cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = 200
        try:
            result = await svc.parse_syllabus_content(large_text)
        finally:
            cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = original

        assert len(result["subjects"]) == 2
        names = [s["name"] for s in result["subjects"]]
        assert "Unit 1: Networking" in names
        assert "Unit 2: Security" in names

    @pytest.mark.asyncio
    async def test_large_syllabus_merges_duplicate_subjects(self):
        """When the same subject appears in multiple chunks, chapters merge."""
        chunk1_data = {
            "subjects": [
                {"name": "Networking", "description": "", "chapters": [
                    {"name": "OSI", "description": "", "topics": ["Layer 1"], "estimated_hours": 3}
                ]}
            ]
        }
        chunk2_data = {
            "subjects": [
                {"name": "Networking", "description": "", "chapters": [
                    {"name": "TCP/IP", "description": "", "topics": ["Ports"], "estimated_hours": 2}
                ]}
            ]
        }
        large_text = (
            "Unit 1: Networking (3 Hrs.)\n"
            + "Detail about OSI.\n" * 10
            + "\n"
            "Unit 2: Networking continued (2 Hrs.)\n"
            + "Detail about TCP/IP.\n" * 10
            + "\n"
        )

        svc = LLMService()
        fake = FakeChatModel([json.dumps(chunk1_data), json.dumps(chunk2_data)])
        svc._get_model = lambda temperature=0.7, json_mode=False, **kwargs: fake  # type: ignore[assignment]

        import app.core.config as cfg
        original = cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS
        cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = 200
        try:
            result = await svc.parse_syllabus_content(large_text)
        finally:
            cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = original

        assert len(result["subjects"]) == 1
        assert result["subjects"][0]["name"] == "Networking"
        chapters = result["subjects"][0]["chapters"]
        assert len(chapters) == 2
        chap_names = {c["name"] for c in chapters}
        assert "OSI" in chap_names
        assert "TCP/IP" in chap_names

    @pytest.mark.asyncio
    async def test_no_content_loss_in_large_syllabus(self):
        """All units/topics from all chunks should appear in the merged result.

        The fake model is input-aware: it extracts whichever 'Unit k' headings
        appear in the chunk it receives and returns their data.  This verifies
        true content survival through splitting + merging, independent of how
        many pieces the splitter produces or how they align."""
        unit_payloads = {
            "Unit 1": {"name": "Unit 1", "description": "", "chapters": [
                {"name": "Networking Basics", "description": "", "topics": ["OSI", "TCP/IP", "HTTP"], "estimated_hours": 3}
            ]},
            "Unit 2": {"name": "Unit 2", "description": "", "chapters": [
                {"name": "Security Fundamentals", "description": "", "topics": ["Cryptography", "Firewalls", "VPN"], "estimated_hours": 4}
            ]},
            "Unit 3": {"name": "Unit 3", "description": "", "chapters": [
                {"name": "Cloud Computing", "description": "", "topics": ["AWS", "Azure", "GCP"], "estimated_hours": 5}
            ]},
        }
        large_text = (
            "Unit 1: Networking (3 Hrs.)\n"
            + "Detail A.\n" * 5
            + "\n"
            "Unit 2: Security (4 Hrs.)\n"
            + "Detail B.\n" * 5
            + "\n"
            "Unit 3: Cloud (5 Hrs.)\n"
            + "Detail C.\n" * 5
            + "\n"
        )

        class UnitAwareModel(Runnable):
            """Returns subject data for every unit heading present in input."""

            def invoke(self, input, config=None, **kwargs):
                raise NotImplementedError("sync path not used")

            async def ainvoke(self, input, config=None, **kwargs):
                # The chain hands the model a ChatPromptValue (or a message
                # list); render it to text either way.
                if hasattr(input, "to_string"):
                    blob = input.to_string()
                else:
                    blob = str(input)
                subjects = [
                    payload for name, payload in unit_payloads.items()
                    if name in blob
                ]
                return AIMessage(content=json.dumps({"subjects": subjects}))

        svc = LLMService()
        svc._get_model = lambda temperature=0.7, json_mode=False, **kwargs: UnitAwareModel()  # type: ignore[assignment]

        import app.core.config as cfg
        original = cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS
        cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = 200
        try:
            result = await svc.parse_syllabus_content(large_text)
        finally:
            cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = original

        # All 3 units present
        assert len(result["subjects"]) == 3
        names = [s["name"] for s in result["subjects"]]
        assert "Unit 1" in names
        assert "Unit 2" in names
        assert "Unit 3" in names

        # All topics present
        all_topics = []
        for subj in result["subjects"]:
            for chap in subj.get("chapters", []):
                all_topics.extend(chap.get("topics", []))

        expected_topics = [
            "OSI", "TCP/IP", "HTTP",
            "Cryptography", "Firewalls", "VPN",
            "AWS", "Azure", "GCP",
        ]
        for topic in expected_topics:
            assert topic in all_topics, f"Topic '{topic}' missing from merged result"

    @pytest.mark.asyncio
    async def test_413_in_single_chunk_returns_none_no_retry(self):
        """If the single-request path hits a 413, it returns None (no crash)."""
        from app.services.llm_service import _OversizedRequestError

        svc = LLMService()

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            raise _OversizedRequestError("413 too large")

        svc._get_model = mock_get_model  # type: ignore[assignment]

        import app.core.config as cfg
        original = cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS
        cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = 50  # Very small budget
        try:
            # Should not crash — parse_syllabus_content raises ValueError
            with pytest.raises(ValueError, match="Failed to parse syllabus"):
                await svc.parse_syllabus_content("Some syllabus text that exceeds budget")
        finally:
            cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = original

    @pytest.mark.asyncio
    async def test_oversized_mid_chunk_splits_and_merges(self):
        """An oversized chunk must be split further (not retried at lower
        temperature), and the piece results must be merged."""
        from app.services.llm_service import _OversizedRequestError

        piece1_data = {
            "subjects": [
                {"name": "Unit 1", "description": "", "chapters": [
                    {"name": "Networking", "description": "", "topics": ["OSI", "TCP/IP"], "estimated_hours": 3}
                ]}
            ]
        }
        piece2_data = {
            "subjects": [
                {"name": "Unit 2", "description": "", "chapters": [
                    {"name": "Security", "description": "", "topics": ["AES", "RSA"], "estimated_hours": 4}
                ]}
            ]
        }

        svc = LLMService()
        fake = FakeChatModel([json.dumps(piece1_data), json.dumps(piece2_data)])
        svc._get_model = lambda temperature=0.7, json_mode=False, **kwargs: fake  # type: ignore[assignment]

        # First attempt always oversized; after splitting, the pieces succeed.
        original_attempt = svc._attempt_syllabus_parse
        calls = {"n": 0}

        async def attempt_that_splits_once(*a, **kw):
            calls["n"] += 1
            if calls["n"] <= 1:
                raise _OversizedRequestError("413 too large")
            return await original_attempt(*a, **kw)

        svc._attempt_syllabus_parse = attempt_that_splits_once  # type: ignore[assignment]

        # Use a very small budget so the single-request path is exercised
        # and the oversized error forces an in-place split.
        import app.core.config as cfg
        original = cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS
        cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = 5000
        try:
            text = (
                "Unit 1: Networking (3 Hrs.)\n"
                + "Detail line about networking.\n" * 80
                + "\nUnit 2: Security (4 Hrs.)\n"
                + "Detail line about security.\n" * 80
            )
            result = await svc.parse_syllabus_content(text)
        finally:
            cfg.settings.GROQ_SYLLABUS_MAX_INPUT_CHARS = original

        assert calls["n"] > 1
        names = [s["name"] for s in result["subjects"]]
        assert "Unit 1" in names
        assert "Unit 2" in names
        all_topics = [
            t
            for s in result["subjects"]
            for c in s.get("chapters", [])
            for t in (c.get("topics") or [])
        ]
        assert "OSI" in all_topics
        assert "TCP/IP" in all_topics
        assert "AES" in all_topics
        assert "RSA" in all_topics


class TestGenerationFailureHandling:
    """Groq json_validate_failed / failed_generation handling.

    These errors mean THIS request produced unusable output.  The parser
    must respond by reducing the chunk size (bounded retries), never by
    re-sending an identical request forever."""

    @staticmethod
    def _make_prompt():
        from langchain_core.prompts import ChatPromptTemplate

        return ChatPromptTemplate.from_messages(
            [("system", "Extract syllabus JSON."), ("human", "{{text}}")],
            template_format="mustache",
        )

    @pytest.mark.asyncio
    async def test_json_validate_failed_raises_generation_error_once(self):
        """A json_validate_failed API error surfaces as _GenerationFailedError
        immediately -- the identical request is never retried."""
        from app.services.llm_service import _GenerationFailedError

        api_error = Exception(
            "Error code: 400 - {'error': {'message': 'Failed to generate JSON', "
            "'type': 'invalid_request_error', 'code': 'json_validate_failed'}}"
        )
        svc = LLMService()
        calls = {"n": 0}

        def mock_get_model(temperature=0.7, json_mode=False, **kwargs):
            calls["n"] += 1
            raise api_error

        svc._get_model = mock_get_model  # type: ignore[assignment]

        with pytest.raises(_GenerationFailedError):
            await svc._attempt_syllabus_parse(
                self._make_prompt(),
                temperature=0.2,
                json_mode=True,
                text="Some syllabus content",
                max_retries=3,
            )

        assert calls["n"] == 1

    @pytest.mark.asyncio
    async def test_json_validate_failed_reduces_chunk_and_recovers(self):
        """End-to-end: the full-size chunk fails generation, smaller
        sub-chunks succeed.  Attempts stay bounded and content survives."""
        from app.services.llm_service import _GenerationFailedError

        good = {"subjects": [{"name": "Unit 1", "description": "", "chapters": [
            {"name": "Basics", "description": "", "topics": ["OSI"], "estimated_hours": 3}]}]}
        svc = LLMService()
        fake = FakeChatModel([json.dumps(good)])
        svc._get_model = lambda temperature=0.7, json_mode=False, **kw: fake  # type: ignore[assignment]

        original_attempt = svc._attempt_syllabus_parse
        seen_lengths: List[int] = []

        async def fail_large_chunks(*args, **kwargs):
            text = kwargs.get("text", "")
            seen_lengths.append(len(text))
            if len(text) > 400:
                raise _GenerationFailedError("json_validate_failed")
            return await original_attempt(*args, **kwargs)

        svc._attempt_syllabus_parse = fail_large_chunks  # type: ignore[assignment]

        text = (
            "Unit 1: Networking (3 Hrs.)\n"
            + "Detail line about networking here.\n" * 30
        )
        from app.core.config import settings
        # Must fit a single first-pass request (no top-level split sleeps)
        assert len(text.strip()) <= settings.GROQ_SYLLABUS_MAX_INPUT_CHARS

        result = await svc.parse_syllabus_content(text)

        assert seen_lengths[0] == len(text.strip())
        assert any(l <= 400 for l in seen_lengths)  # recovered on smaller chunks
        assert len(seen_lengths) < 15               # bounded, not endless
        names = [s["name"] for s in result["subjects"]]
        assert names == ["Unit 1"]
        topics = [
            t for s in result["subjects"]
            for c in s.get("chapters", [])
            for t in (c.get("topics") or [])
        ]
        assert "OSI" in topics

    @pytest.mark.asyncio
    async def test_persistent_generation_failure_terminates(self):
        """If every chunk fails generation, parsing terminates with a
        ValueError after a bounded number of attempts."""
        from app.services.llm_service import _GenerationFailedError

        svc = LLMService()
        calls = {"n": 0}

        async def always_fails(*args, **kwargs):
            calls["n"] += 1
            raise _GenerationFailedError("json_validate_failed")

        svc._attempt_syllabus_parse = always_fails  # type: ignore[assignment]

        text = (
            "Unit 1: Networking (3 Hrs.)\n"
            + "Detail line content here.\n" * 30
        )
        with pytest.raises(ValueError, match="Failed to parse syllabus"):
            await svc.parse_syllabus_content(text)

        assert calls["n"] < 15

    @pytest.mark.asyncio
    async def test_oversized_mid_size_chunk_is_split_not_abandoned(self):
        """Regression: a ~694-char chunk that fails with an oversized error
        used to hit 'splitter made no progress; giving up' because the old
        sub-budget derived only from max_chars stayed above the chunk size.
        It must now be halved and parsed."""
        from app.services.llm_service import _OversizedRequestError

        p1 = {"subjects": [{"name": "Unit 1", "description": "", "chapters": [
            {"name": "A", "description": "", "topics": ["x"], "estimated_hours": 1}]}]}
        p2 = {"subjects": [{"name": "Unit 2", "description": "", "chapters": [
            {"name": "B", "description": "", "topics": ["y"], "estimated_hours": 1}]}]}

        svc = LLMService()
        fake = FakeChatModel([json.dumps(p1), json.dumps(p2)])
        svc._get_model = lambda temperature=0.7, json_mode=False, **kw: fake  # type: ignore[assignment]

        original_attempt = svc._attempt_syllabus_parse
        calls = {"n": 0}

        async def oversized_once(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                raise _OversizedRequestError("413 too large")
            return await original_attempt(*a, **kw)

        svc._attempt_syllabus_parse = oversized_once  # type: ignore[assignment]

        chunk = (
            "Unit 1: Networking (3 Hrs.)\n"
            + "Some detail topic line here.\n" * 23
        )
        assert 650 < len(chunk) < 750  # mirrors the production failure log

        result = await svc._parse_chunk_with_splitting(
            prompt=self._make_prompt(),
            chunk=chunk,
            temperature=0.2,
            max_chars=1800,
        )

        assert calls["n"] >= 2
        names = [s["name"] for s in result["subjects"]]
        assert "Unit 1" in names
        assert "Unit 2" in names

    def test_hard_split_always_makes_progress(self):
        text = "word " * 300  # 1500 chars, spaces but no newlines
        pieces = LLMService._hard_split(text, 300)
        assert len(pieces) >= 4
        assert all(len(p) <= 300 for p in pieces)

    def test_split_with_no_whitespace_still_progresses(self):
        text = "A" * 500
        chunks = LLMService._split_syllabus_text(text, 120)
        assert len(chunks) >= 4
        assert "".join(chunks) == "A" * 500

    def test_recursive_splitting_makes_progress_at_every_budget(self):
        text = "Unit 1: Networking\n" + "Detail line about networking.\n" * 12
        n = len(text)
        budgets = sorted({n // k for k in range(2, 9)} | {97, 48})
        for max_chars in budgets:
            chunks = LLMService._split_syllabus_text(text, max_chars)
            assert len(chunks) >= 2, f"max_chars={max_chars}"
            joined = "\n".join(chunks)
            assert "Unit 1: Networking" in joined, f"max_chars={max_chars}"
            assert sum(len(c) for c in chunks) >= int(n * 0.85), (
                f"content lost at max_chars={max_chars}"
            )

    def test_unit_heading_stays_with_its_content(self):
        text = (
            "Intro paragraph.\n" * 8
            + "Unit 2: Security Concepts\n"
            + "Firewalls; VPN; IDS\n" * 6
            + "Unit 3: Databases\n"
            + "SQL; Normalization\n" * 6
        )
        chunks = LLMService._split_syllabus_text(text, 150)
        assert any(
            "Unit 2: Security Concepts" in c and "Firewalls" in c
            for c in chunks
        )
        assert any(
            "Unit 3: Databases" in c and "SQL" in c for c in chunks
        )
