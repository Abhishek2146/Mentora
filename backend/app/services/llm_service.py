"""
LLM Service - handles AI language model interactions.

Supports both Groq and OpenAI providers. Prefers Groq if
GROQ_API_KEY is configured, falls back to OpenAI if
OPENAI_API_KEY is available.
"""

import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    Service for interacting with LLMs (Groq or OpenAI).

    The model client is initialized lazily so the backend can
    start even when no API key is configured. The actual error
    is raised only when a generation is attempted.
    """

    def __init__(self):
        self.model: Optional[ChatGroq] = None
        self.parser = StrOutputParser()
        self._model_cache_key: Optional[tuple] = None
        
    
    def _get_model(
        self,
        temperature: float = 0.7,
        json_mode: bool = False,
    ) -> ChatGroq:
        """
        Initialize the Groq model only when it is needed.

        When ``json_mode`` is True the model is configured with Groq's
        JSON-mode ``response_format`` so the provider is constrained to
        emit valid JSON.
        """
        cache_key = (temperature, json_mode)
        if self.model is None or cache_key != self._model_cache_key:
            if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("your_"):
                raise RuntimeError(
                    "GROQ_API_KEY is not configured. "
                    "Add it to your backend .env file before using AI features."
                )

            model_kwargs: Dict[str, Any] = {}
            if json_mode:
                model_kwargs["response_format"] = {"type": "json_object"}

            self.model = ChatGroq(
                model=settings.GROQ_MODEL,
                api_key=settings.GROQ_API_KEY,
                temperature=temperature,
                model_kwargs=model_kwargs,
            )
            self._model_cache_key = cache_key
        return self.model

    @staticmethod
    def _extract_json(result: str) -> str:
        """
        Extract a JSON string from LLM output.

        Handles Markdown code fences and any extra explanatory text that
        the LLM may prepend or append to the JSON payload.  If the entire
        response is already valid JSON it is returned as-is; otherwise the
        first balanced JSON object or array is extracted via brace-matching.
        """
        result = result.strip()

        # Strip markdown code fences
        if result.startswith("```json"):
            result = result[len("```json"):]
        elif result.startswith("```"):
            result = result[len("```"):]
        result = result.removesuffix("```")
        result = result.strip()

        # Fast path: the whole string is already valid JSON
        try:
            json.loads(result)
            return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: locate the first balanced JSON object or array and
        # extract it, ignoring any surrounding prose / markdown.
        # Determine which opener ('{' or '[') appears first in the text.
        brace_start = result.find("{")
        bracket_start = result.find("[")
        candidates: List[tuple] = []
        if brace_start != -1:
            candidates.append((brace_start, "{", "}"))
        if bracket_start != -1:
            candidates.append((bracket_start, "[", "]"))
        candidates.sort()

        for start, opener, closer in candidates:
            depth = 0
            in_string = False
            escape = False
            for i in range(start, len(result)):
                ch = result[i]
                if in_string:
                    if escape:
                        escape = False
                    elif ch == "\\":
                        escape = True
                    elif ch == '"':
                        in_string = False
                else:
                    if ch == '"':
                        in_string = True
                    elif ch == opener:
                        depth += 1
                    elif ch == closer:
                        depth -= 1
                        if depth == 0:
                            candidate = result[start : i + 1]
                            try:
                                json.loads(candidate)
                                return candidate
                            except (json.JSONDecodeError, ValueError):
                                break

        # Last resort: best-effort regex grab between the first '{' and
        # last '}' (or '[' and ']').
        match = re.search(r"\{.*\}", result, re.DOTALL)
        if match:
            candidate = match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except (json.JSONDecodeError, ValueError):
                pass
        match = re.search(r"\[.*\]", result, re.DOTALL)
        if match:
            candidate = match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except (json.JSONDecodeError, ValueError):
                pass

        return result

    async def generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Generate a response from the LLM."""
        model = self._get_model(temperature=temperature)
        response = await model.ainvoke(prompt)
        return response.content

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Generate a chat response from a list of messages."""
        prompt = ChatPromptTemplate.from_messages(messages)
        model = self._get_model(temperature=temperature)
        chain = prompt | model | self.parser
        return await chain.ainvoke({})

    async def parse_syllabus_content(
        self,
        text: str,
    ) -> dict:
        """
        Parse syllabus text into structured academic data.

        Uses Groq JSON mode (``response_format: {"type": "json_object"}``)
        to constrain the LLM output to valid JSON, with a robust extraction
        fallback for any residual markdown/wrapper text.  The parsed result
        is validated against the expected schema before being returned.

        On failure a ``ValueError`` is raised (caught by the calling
        SyllabusService) rather than silently returning empty subjects.
        """

        system_prompt = """
You are an expert educational content analyzer.

Analyze the provided syllabus and extract its academic structure.

A syllabus typically contains one or more units (often labeled
"Unit 1", "Unit I", "Module 1", or similar).  Each unit heading has
the format: "Unit N: Title (H Hrs.)" and is followed by a list of
topics, usually separated by semicolons or as bullet points.

Extract the structure as follows:
- Each unit heading (e.g. "Unit 1: Introduction to Computer (3 Hrs.)")
  becomes ONE Subject.  Use only the unit title (without the "Unit N:"
  prefix or the hours in parentheses) as the subject name.
- Create ONE Chapter per Subject.  That chapter holds:
  - the list of topics for that unit (split on semicolons or bullets)
  - the estimated_hours: the integer from the "(N Hrs.)",
    "(N Hours)", "(N hr)", or "(N hours)" pattern on the unit line.
    If no hours are found, use 0.
- If the syllabus has explicit sub-chapters within a unit, create one
  chapter per sub-chapter instead, each with its own topics and
  estimated_hours if available.

IMPORTANT: Return ONLY valid JSON. The entire response must be a
valid JSON object. Do NOT include any markdown formatting, code fences,
or explanatory text outside the JSON.

Required structure:

{{
    "subjects": [
        {{
            "name": "Unit Title",
            "description": "Subject description",
            "chapters": [
                {{
                    "name": "Chapter Name",
                    "description": "Chapter description",
                    "topics": [
                        "Topic 1",
                        "Topic 2"
                    ],
                    "estimated_hours": 3
                }}
            ]
        }}
    ]
}}
"""

        human_prompt = f"""
Parse the following syllabus content:

{text}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )

        # Attempt 1: Groq JSON mode at the configured temperature.
        result = await self._attempt_syllabus_parse(
            prompt,
            temperature=settings.GROQ_TEMPERATURE,
            json_mode=True,
        )
        if result is not None:
            return result

        logger.warning(
            "Syllabus JSON parse failed (temp=%s); retrying with lower "
            "temperature.",
            settings.GROQ_TEMPERATURE,
        )

        # Attempt 2: JSON mode at a lower, more deterministic temperature.
        result = await self._attempt_syllabus_parse(
            prompt, temperature=0.2, json_mode=True
        )
        if result is not None:
            return result

        logger.warning(
            "Syllabus JSON parse failed (temp=0.2); retrying without "
            "JSON-mode constraint but with robust extraction."
        )

        # Attempt 3: No JSON-mode constraint - fall back to robust
        # extraction from a free-form response.
        result = await self._attempt_syllabus_parse(
            prompt, temperature=0.2, json_mode=False
        )
        if result is not None:
            return result

        raise ValueError(
            "Failed to parse syllabus into valid JSON after multiple attempts."
        )

    async def _attempt_syllabus_parse(
        self,
        prompt: ChatPromptTemplate,
        temperature: float,
        json_mode: bool,
    ) -> Optional[dict]:
        """Try a single syllabus-parse attempt.

        Returns the validated, parsed dict on success, or ``None`` on
        any failure so the caller can fall back to another strategy.
        """
        try:
            model = self._get_model(
                temperature=temperature, json_mode=json_mode
            )
            chain = prompt | model | self.parser
            result = await chain.ainvoke({})

            cleaned = self._extract_json(result)
            data = json.loads(cleaned)
            data = self._validate_syllabus_data(data)

            if not data.get("subjects"):
                raise ValueError("Parsed syllabus contains no subjects")

            return data

        except RuntimeError:
            # Configuration errors (e.g. missing/invalid API key) are not
            # transient - retry will not help, so let them propagate.
            raise
        except Exception as exc:
            logger.warning(
                "Syllabus parse attempt failed "
                "(temperature=%s, json_mode=%s): %s",
                temperature,
                json_mode,
                exc,
            )
            return None

    @staticmethod
    def _validate_syllabus_data(data: Any) -> dict:
        """Validate the structure of parsed syllabus data.

        Returns the validated dict, or raises ``ValueError`` with a
        descriptive message when the structure is invalid.
        """
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected a JSON object at the top level, "
                f"got {type(data).__name__}"
            )

        subjects = data.get("subjects")
        if not isinstance(subjects, list):
            raise ValueError("'subjects' must be a list")

        for i, subj in enumerate(subjects):
            if not isinstance(subj, dict):
                raise ValueError(f"Subject at index {i} must be an object")
            if not subj.get("name"):
                raise ValueError(f"Subject at index {i} is missing 'name'")

            chapters = subj.get("chapters", [])
            if not isinstance(chapters, list):
                raise ValueError(
                    f"Subject '{subj.get('name')}' chapters must be a list"
                )

            for j, chap in enumerate(chapters):
                if not isinstance(chap, dict):
                    raise ValueError(
                        f"Chapter at index {j} in subject "
                        f"'{subj.get('name')}' must be an object"
                    )
                if not chap.get("name"):
                    raise ValueError(
                        f"Chapter at index {j} in subject "
                        f"'{subj.get('name')}' is missing 'name'"
                    )

                topics = chap.get("topics")
                if topics is not None and not isinstance(topics, list):
                    raise ValueError(
                        f"Chapter '{chap.get('name')}' topics must be a list"
                    )

        return data

    async def generate_quiz_questions(
        self,
        content: str,
        num_questions: int = 10,
        difficulty: str = "medium",
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple-choice quiz questions.
        """

        system_prompt = f"""
You are an expert educational quiz generator.

Generate {num_questions} multiple-choice questions
from the provided content.

Difficulty: {difficulty}

Each question must contain:

- question_text
- options
- correct_answer
- explanation

The options must contain exactly four choices.

Return ONLY a valid JSON array.

Example:

[
    {{
        "question_text": "Example question?",
        "options": ["A", "B", "C", "D"],
        "correct_answer": "A",
        "explanation": "Explanation"
    }}
]
"""

        human_prompt = f"""
Generate quiz questions from:

{content}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )

        model = self._get_model()
        chain = prompt | model | self.parser

        result = await chain.ainvoke({})
        try:
            cleaned = self._extract_json(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "LLM returned invalid JSON for quiz generation."
            )
            return []

    async def generate_flashcards(
        self,
        content: str,
        num_cards: int = 10,
    ) -> List[Dict[str, str]]:
        """
        Generate flashcards from educational content.
        """

        system_prompt = f"""
You are an expert flashcard creator.

Create {num_cards} useful educational flashcards
from the provided content.

Each flashcard must contain:

- front
- back

Return ONLY a valid JSON array.
"""

        human_prompt = f"""
Generate flashcards from:

{content}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )

        model = self._get_model()
        chain = prompt | model | self.parser

        result = await chain.ainvoke({})
        try:
            cleaned = self._extract_json(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "LLM returned invalid JSON for flashcards."
            )
            return []

    async def generate_study_plan(
        self,
        syllabus_data: dict,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        Generate a personalized study plan.
        """

        system_prompt = """
You are an expert educational study planner.

Create a detailed study plan based on the syllabus.

The plan should contain:

- daily tasks
- study sessions
- completion goals

Return ONLY valid JSON with:

{{
    "tasks": [],
    "summary": ""
}}
"""

        human_prompt = f"""
Syllabus:

{json.dumps(syllabus_data)}

Start date:
{start_date}

End date:
{end_date}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )

        model = self._get_model()
        chain = prompt | model | self.parser

        result = await chain.ainvoke({})
        try:
            cleaned = self._extract_json(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            return {
                "tasks": [],
                "summary": result,
            }

    async def generate_revision_schedule(
        self,
        syllabus_data: dict,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        Generate a spaced-repetition revision schedule.
        """

        system_prompt = """
You are an expert educational revision planner.

Create a spaced repetition revision schedule.

Return ONLY valid JSON:

{{
    "items": [
        {{
            "topic": "Topic name",
            "scheduled_date": "YYYY-MM-DD",
            "difficulty": "easy/medium/hard"
        }}
    ]
}}
"""

        human_prompt = f"""
Syllabus:

{json.dumps(syllabus_data)}

Start date:
{start_date}

End date:
{end_date}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )

        model = self._get_model()
        chain = prompt | model | self.parser

        result = await chain.ainvoke({})
        try:
            cleaned = self._extract_json(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            return {"items": []}

    async def analyze_weak_topics(
        self,
        quiz_results: List[dict],
        syllabus_data: dict,
    ) -> List[dict]:
        """
        Analyze quiz results and identify weak topics.
        """

        system_prompt = """
You are an educational analytics expert.

Analyze quiz results and identify weak topics.

For each weak topic return:

- topic_name
- accuracy
- confidence_level
- recommended_action

Return ONLY a valid JSON array.
"""

        human_prompt = f"""
Quiz results:

{json.dumps(quiz_results)}

Syllabus:

{json.dumps(syllabus_data)}
"""

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ]
        )

        model = self._get_model()
        chain = prompt | model | self.parser

        result = await chain.ainvoke({})
        try:
            cleaned = self._extract_json(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "LLM returned invalid JSON for weak-topic analysis."
            )
            return []
