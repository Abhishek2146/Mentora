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
    svc._get_model = lambda temperature=0.7, json_mode=False: fake  # type: ignore[assignment]
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
        with pytest.raises(ValueError, match="subjects.*list"):
            LLMService._validate_syllabus_data({"subjects": "not a list"})

    def test_subject_missing_name(self):
        with pytest.raises(ValueError, match="missing 'name'"):
            LLMService._validate_syllabus_data(
                {"subjects": [{"chapters": []}]}
            )

    def test_chapter_missing_name(self):
        with pytest.raises(ValueError, match="missing 'name'"):
            LLMService._validate_syllabus_data(
                {"subjects": [{"name": "Math", "chapters": [{"topics": []}]}]}
            )

    def test_topics_not_a_list(self):
        with pytest.raises(ValueError, match="topics.*list"):
            LLMService._validate_syllabus_data(
                {
                    "subjects": [
                        {
                            "name": "Math",
                            "chapters": [{"name": "Ch1", "topics": "not a list"}],
                        }
                    ]
                }
            )


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
                    "chapters": [
                        {"name": "Atoms", "topics": ["Atomic structure"], "estimated_hours": 3}
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
                    "chapters": [
                        {
                            "name": "Mechanics",
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
                    "chapters": [
                        {"name": "Algebra", "topics": ["x"], "estimated_hours": 2}
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

        def mock_get_model(temperature=0.7, json_mode=False):
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
        data = {"subjects": [{"name": "Test", "chapters": []}]}
        svc = LLMService()
        fake = FakeChatModel([json.dumps(data)])

        json_mode_calls: List[bool] = []

        def mock_get_model(temperature=0.7, json_mode=False):
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
                    "chapters": [{"name": "Cells", "topics": ["Mitosis"], "estimated_hours": 2}],
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
                            "topics": ["Linear Regression", "Logistic Regression",
                                     "Decision Trees", "SVM"],
                            "estimated_hours": 8,
                        },
                        {
                            "name": "Unsupervised Learning",
                            "topics": ["K-Means Clustering", "PCA",
                                     "Hierarchical Clustering"],
                            "estimated_hours": 6,
                        },
                        {
                            "name": "Deep Learning",
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
                            "topics": ["Array operations", "Hash maps",
                                     "Two pointers"],
                            "estimated_hours": 5,
                        },
                        {
                            "name": "Tree Algorithms",
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
                    "chapters": [
                        {
                            "name": "OSI Model",
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
