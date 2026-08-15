"""
LLM Service - handles AI language model interactions.

Supports both Groq and OpenAI providers. Prefers Groq if
GROQ_API_KEY is configured, falls back to OpenAI if
OPENAI_API_KEY is available.
"""

import json
from typing import Optional, Dict, Any, List

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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
        self.parser = StrOutputParser()
        self._model = None
        self._provider: str = "unknown"

    def _get_model(self, temperature: float = None):
        """
        Initialize the LLM model lazily based on available API keys.

        Prefers Groq when GROQ_API_KEY is present, otherwise
        falls back to OpenAI when OPENAI_API_KEY is present.
        """
        if self._model is not None:
            if temperature is not None:
                return self._model.bind(temperature=temperature)
            return self._model

        if settings.GROQ_API_KEY:
            from langchain_groq import ChatGroq

            self._provider = "groq"
            model_kwargs: Dict[str, Any] = {
                "api_key": settings.GROQ_API_KEY,
                "model": settings.GROQ_MODEL,
            }
            if temperature is not None:
                model_kwargs["temperature"] = temperature
            else:
                model_kwargs["temperature"] = settings.GROQ_TEMPERATURE
            model_kwargs["max_tokens"] = settings.GROQ_MAX_TOKENS

            self._model = ChatGroq(**model_kwargs)

        elif settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_"):
            from langchain_openai import ChatOpenAI

            self._provider = "openai"
            self._model = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=temperature if temperature is not None else 0.7,
            )

        else:
            raise RuntimeError(
                "No LLM API key configured. Set GROQ_API_KEY or "
                "OPENAI_API_KEY in your environment."
            )

        logger.info(
            "LLM service initialized with provider: %s",
            self._provider,
        )

        return self._model

    @staticmethod
    def _clean_json_response(result: str) -> str:
        """
        Remove Markdown code fences from LLM JSON responses.
        """
        result = result.strip()

        if result.startswith("```json"):
            result = result[7:]

        elif result.startswith("```"):
            result = result[3:]

        if result.endswith("```"):
            result = result[:-3]

        return result.strip()

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
        """

        system_prompt = """
You are an expert educational content analyzer.

Analyze the provided syllabus and extract:

1. Subjects
2. Subject descriptions
3. Chapters for each subject
4. Chapter descriptions
5. Topics inside each chapter

Return ONLY valid JSON.

Required structure:

{
    "subjects": [
        {
            "name": "Subject Name",
            "description": "Subject description",
            "chapters": [
                {
                    "name": "Chapter Name",
                    "description": "Chapter description",
                    "topics": [
                        "Topic 1",
                        "Topic 2"
                    ]
                }
            ]
        }
    ]
}
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

        model = self._get_model()
        chain = prompt | model | self.parser

        result = await chain.ainvoke({})
        try:
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "LLM returned invalid JSON while parsing syllabus."
            )

            return {
                "subjects": [],
                "raw_text": result,
            }

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
            cleaned = self._clean_json_response(result)
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
            cleaned = self._clean_json_response(result)
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

{
    "tasks": [],
    "summary": ""
}
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
            cleaned = self._clean_json_response(result)
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

{
    "items": [
        {
            "topic": "Topic name",
            "scheduled_date": "YYYY-MM-DD",
            "difficulty": "easy/medium/hard"
        }
    ]
}
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
            cleaned = self._clean_json_response(result)
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
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "LLM returned invalid JSON for weak-topic analysis."
            )
            return []
