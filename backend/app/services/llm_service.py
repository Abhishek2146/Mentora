"""
LLM Service - handles AI language model interactions
"""
import json
from typing import Optional, Dict, Any, List

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    Service for interacting with OpenAI models.

    The OpenAI client is initialized lazily so that the
    backend can start even when OPENAI_API_KEY is not
    configured.
    """

    def __init__(self):
        self.model: Optional[ChatOpenAI] = None
        self.parser = StrOutputParser()

    def _get_model(self, temperature: float = 0.7) -> ChatOpenAI:
        """
        Initialize the OpenAI model only when it is needed.
        """
        if self.model is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_"):
                raise RuntimeError(
                    "OPENAI_API_KEY is not configured. "
                    "Add it to your backend .env file before using AI features."
                )

            self.model = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.OPENAI_API_KEY,
                temperature=temperature,
            )
        return self.model

    async def generate(self, prompt: str) -> str:
        """Generate a response from the LLM."""
        model = self._get_model()
        response = await model.ainvoke(prompt)
        return response.content

    async def parse_syllabus_content(self, text: str) -> dict:
        """Parse syllabus text into structured data using LLM."""
        system_prompt = """
You are an expert educational content analyzer. Extract the following information:
1. List of subjects with their names and descriptions
2. For each subject, list of chapters with names and descriptions
3. Identify topic names within each chapter
4. Return as valid JSON with structure: {{
  "subjects": [
    {{
      "name": "Subject Name",
      "description": "Description",
      "chapters": [
        {{
          "name": "Chapter Name",
          "description": "Description",
          "topics": ["Topic 1", "Topic 2"]
        }}
      ]
    }}
  ]
}}
"""
        human_prompt = f"Parse this syllabus content:\n\n{text}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | self._get_model() | self.parser
        result = await chain.ainvoke({})
        try:
            return json.loads(result.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return {"subjects": [], "raw_text": result}

    async def generate_quiz_questions(
        self, content: str, num_questions: int = 10, difficulty: str = "medium"
    ) -> List[Dict[str, Any]]:
        """Generate quiz questions from content."""
        system_prompt = f"""
You are an expert quiz generator. Generate {num_questions} multiple choice questions 
from the given content at {difficulty} difficulty. Each question should have:
- question_text: the question
- options: list of 4 options (A, B, C, D)
- correct_answer: the correct option letter
- explanation: detailed explanation

Return as JSON array.
"""
        human_prompt = f"Generate questions from:\n\n{content}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | self._get_model() | self.parser
        result = await chain.ainvoke({})
        try:
            return json.loads(result.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return []

    async def generate_flashcards(self, content: str, num_cards: int = 10) -> List[Dict[str, str]]:
        """Generate flashcards from content."""
        system_prompt = f"""
You are an expert flashcard creator. Create {num_cards} flashcards from the given content.
Each flashcard should have a front (term/question) and back (definition/answer).
Return as JSON array of objects with 'front' and 'back' fields.
"""
        human_prompt = f"Generate flashcards from:\n\n{content}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | self._get_model() | self.parser
        result = await chain.ainvoke({})
        try:
            return json.loads(result.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return []

    async def generate_study_plan(
        self, syllabus_data: dict, start_date: str, end_date: Optional[str] = None
    ) -> dict:
        """Generate a study plan from syllabus data."""
        system_prompt = """
You are an expert study planner. Create a detailed study plan from the given syllabus.
Plan should include daily tasks, study sessions, and completion goals.
Return as JSON object with 'tasks' array and 'summary' string.
"""
        human_prompt = f"""
Create a study plan from this syllabus: {json.dumps(syllabus_data)}
Start date: {start_date}
End date: {end_date}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | self._get_model() | self.parser
        result = await chain.ainvoke({})
        try:
            return json.loads(result.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return {"tasks": [], "summary": result}

    async def generate_revision_schedule(
        self, syllabus_data: dict, start_date: str, end_date: Optional[str] = None
    ) -> dict:
        """Generate a revision schedule."""
        system_prompt = """
You are an expert revision planner. Create a spaced repetition revision schedule.
Return as JSON with 'items' array containing topic, scheduled_date, and difficulty.
"""
        human_prompt = f"""
Create revision schedule from: {json.dumps(syllabus_data)}
Start: {start_date}, End: {end_date}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | self._get_model() | self.parser
        result = await chain.ainvoke({})
        try:
            return json.loads(result.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return {"items": []}

    async def chat_completion(
        self, messages: List[Dict[str, str]], temperature: float = 0.7
    ) -> str:
        """Generate a chat completion."""
        prompt = ChatPromptTemplate.from_messages(messages)
        chain = prompt | self._get_model(temperature) | self.parser
        result = await chain.ainvoke({})
        return result

    async def analyze_weak_topics(
        self, quiz_results: List[dict], syllabus_data: dict
    ) -> List[dict]:
        """Analyze quiz results to identify weak topics."""
        system_prompt = """
You are an educational analytics expert. Analyze the quiz results to identify weak topics.
Return JSON array of objects with: topic_name, accuracy, confidence_level, recommended_action.
"""
        human_prompt = f"""
Quiz results: {json.dumps(quiz_results)}
Syllabus: {json.dumps(syllabus_data)}
"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", human_prompt),
        ])
        chain = prompt | self._get_model() | self.parser
        result = await chain.ainvoke({})
        try:
            return json.loads(result.replace("```json", "").replace("```", "").strip())
        except json.JSONDecodeError:
            return []
