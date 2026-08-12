"""
LLM Service - handles AI language model interactions using Groq.
"""

import json
from typing import Optional, Dict, Any, List

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger(__name__)


class LLMService:
    """
    Service for interacting with Groq LLMs.
    """

    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not configured in the environment."
            )

        self.api_key = settings.GROQ_API_KEY
        self.model_name = settings.GROQ_MODEL

        self.model = ChatGroq(
            api_key=self.api_key,
            model=self.model_name,
            temperature=settings.GROQ_TEMPERATURE,
            max_tokens=settings.GROQ_MAX_TOKENS,
        )

        self.parser = StrOutputParser()

        logger.info(
            "LLM service initialized with Groq model: %s",
            self.model_name,
        )

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

        chain = prompt | self.model | self.parser

        result = await chain.ainvoke({})

        try:
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "Groq returned invalid JSON while parsing syllabus."
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

        chain = prompt | self.model | self.parser

        result = await chain.ainvoke({})

        try:
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "Groq returned invalid JSON for quiz generation."
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

        chain = prompt | self.model | self.parser

        result = await chain.ainvoke({})

        try:
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "Groq returned invalid JSON for flashcards."
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

        chain = prompt | self.model | self.parser

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

        chain = prompt | self.model | self.parser

        result = await chain.ainvoke({})

        try:
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            return {"items": []}

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """
        Generate a chat response using Groq.
        """

        prompt_messages = [
            (
                message.get("role", "user"),
                message.get("content", ""),
            )
            for message in messages
        ]

        prompt = ChatPromptTemplate.from_messages(prompt_messages)

        model = self.model.bind(
            temperature=temperature
        )

        chain = prompt | model | self.parser

        result = await chain.ainvoke({})

        return result

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

        chain = prompt | self.model | self.parser

        result = await chain.ainvoke({})

        try:
            cleaned = self._clean_json_response(result)
            return json.loads(cleaned)

        except json.JSONDecodeError:
            logger.warning(
                "Groq returned invalid JSON for weak-topic analysis."
            )
            return []