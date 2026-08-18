"""
LLM Service - handles AI language model interactions.

Supports both Groq and OpenAI providers. Prefers Groq if
GROQ_API_KEY is configured, falls back to OpenAI if
OPENAI_API_KEY is available.
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class _OversizedRequestError(Exception):
    """Raised when the LLM request exceeds the model's input size limit.

    This is NOT a transient error — retrying with the same input will
    fail again.  The caller should reduce the chunk size or split the
    input further rather than retrying.
    """


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
                max_tokens=settings.GROQ_MAX_TOKENS,
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
        """Generate a chat response from a list of messages.

        Uses BaseMessage objects directly instead of ChatPromptTemplate
        to avoid f-string template issues with curly braces in content.
        """
        model = self._get_model(temperature=temperature)
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        return await model.ainvoke(lc_messages)

    async def parse_syllabus_content(
        self,
        text: str,
    ) -> dict:
        """
        Parse syllabus text into structured academic data.

        If the text fits within the model's input budget, it is sent in
        a single request.  Otherwise it is split on structural headings
        (Unit / Module / Chapter / …) and each chunk is parsed separately;
        the results are merged before being returned.

        Uses Groq JSON mode (``response_format: {"type": "json_object"}``)
        to constrain the LLM output to valid JSON, with a robust extraction
        fallback for any residual markdown/wrapper text.  The parsed result
        is validated against the expected schema before being returned.

        On failure a ``ValueError`` is raised (caught by the calling
        SyllabusService) rather than silently returning empty subjects.
        """

        max_input_chars = settings.GROQ_SYLLABUS_MAX_INPUT_CHARS

        system_prompt = (
            "You are an expert educational content analyzer.\n"
            "\n"
            "TASK: Extract the academic structure from the syllabus provided\n"
            "inside <SYLLABUS_CONTENT> tags.\n"
            "\n"
            "RULES:\n"
            "- Output EXACTLY ONE valid JSON object.\n"
            "- Do NOT include markdown, code fences, comments, or any text\n"
            "  outside the JSON object.\n"
            "- Use double quotes for all keys and string values.\n"
            "- No trailing commas.\n"
            "- Do NOT invent content that is not in the syllabus.\n"
            "- Do NOT add DBMS, computer-science, or other dummy content.\n"
            "\n"
            "CRITICAL STRUCTURE RULES:\n"
            "- The top-level JSON object MUST contain a \"subjects\" key.\n"
            "- \"subjects\" MUST ALWAYS be an array (list), never a string\n"
            "  or object.\n"
            "- Every element in \"subjects\" MUST be an object.\n"
            "- Every subject object MUST contain \"name\" (string) and\n"
            "  \"chapters\" (array).\n"
            "- \"chapters\" MUST ALWAYS be an array (list), never a string\n"
            "  or object.\n"
            "- Every element in \"chapters\" MUST be an object.\n"
            "- Every chapter object MUST contain \"name\" (string),\n"
            "  \"description\" (string), \"topics\" (array of strings),\n"
            "  and \"estimated_hours\" (integer).\n"
            "- \"topics\" MUST ALWAYS be an array of strings, never a\n"
            "  single string.\n"
            "- NEVER return chapters as plain strings.\n"
            "- NEVER return subjects as plain strings.\n"
            "- NEVER return topics as a single string.\n"
            "\n"
            "UNIT HEADINGS:\n"
            "Recognize patterns like: Unit 1, Unit I, Module 1, Chapter 1,\n"
            "or similar headings. Each becomes ONE subject.\n"
            "Use only the unit title (without the 'Unit N:' prefix or\n"
            "hours in parentheses) as the subject name.\n"
            "\n"
            "HOURS:\n"
            "Extract the integer from patterns like '(3 Hrs.)', '(6 Hours)',\n"
            "'(2 hr)'. If no hours found, use 0.\n"
            "\n"
            "TOPICS:\n"
            "Split semicolon-separated and bullet-point topics into a list.\n"
            "\n"
            "OUTPUT SCHEMA:\n"
            "{\n"
            '  "subjects": [\n'
            "    {\n"
            '      "name": "Unit Title",\n'
            '      "description": "Brief description",\n'
            '      "chapters": [\n'
            "        {\n"
            '          "name": "Chapter Name",\n'
            '          "description": "Brief description",\n'
            '          "topics": ["Topic 1", "Topic 2"],\n'
            '          "estimated_hours": 3\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "EXAMPLE - correct output for 'Unit 1: Networking (3 Hrs.)'\n"
            "with topics 'OSI Model' and 'TCP/IP':\n"
            "{\n"
            '  "subjects": [\n'
            "    {\n"
            '      "name": "Networking",\n'
            '      "description": "Unit 1",\n'
            '      "chapters": [\n'
            "        {\n"
            '          "name": "Networking Overview",\n'
            '          "description": "",\n'
            '          "topics": ["OSI Model", "TCP/IP"],\n'
            '          "estimated_hours": 3\n'
            "        }\n"
            "      ]\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "Return ONLY the JSON object. Nothing else."
        )

        human_prompt = (
            "<SYLLABUS_CONTENT>\n"
            "{{text}}\n"
            "</SYLLABUS_CONTENT>\n"
            "\n"
            "Extract the academic structure as a JSON object."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", human_prompt),
            ],
            template_format="mustache",
        )

        # --- Try single-request first ----------------------------------
        if len(text) <= max_input_chars:
            result = await self._parse_single_chunk(
                prompt, text, settings.GROQ_TEMPERATURE
            )
            if result is None:
                raise ValueError(
                    "Failed to parse syllabus: the LLM did not return valid "
                    "JSON after multiple attempts."
                )
            return result

        # --- Text is too large — split into chunks ---------------------
        chunks = self._split_syllabus_text(text, max_input_chars)
        num_chunks = len(chunks)
        logger.info(
            "Syllabus exceeds single-request budget (%d chars > %d); "
            "splitting into %d chunks",
            len(text),
            max_input_chars,
            num_chunks,
        )

        chunk_results: List[dict] = []
        for i, chunk in enumerate(chunks, 1):
            logger.info("Parsing syllabus chunk %d/%d", i, num_chunks)
            parsed = await self._parse_single_chunk(
                prompt, chunk, settings.GROQ_TEMPERATURE
            )
            if parsed:
                chunk_results.append(parsed)

        if not chunk_results:
            raise ValueError(
                "Failed to parse any syllabus chunk into valid JSON."
            )

        if len(chunk_results) == 1:
            logger.info("Successfully parsed syllabus in 1 chunk")
            return chunk_results[0]

        merged = self._merge_syllabus_chunks(chunk_results)
        total_subjects = len(merged.get("subjects", []))
        logger.info(
            "Successfully merged %d syllabus chunks (%d subjects)",
            num_chunks,
            total_subjects,
        )
        return merged

    async def _parse_single_chunk(
        self,
        prompt: ChatPromptTemplate,
        text: str,
        temperature: float,
    ) -> Optional[dict]:
        """Parse a single chunk of syllabus text using the 3-attempt strategy.

        Returns the validated dict on success, or ``None`` if all attempts
        fail (including oversized-request errors, which are not retried).
        """
        # Attempt 1: Groq JSON mode at the configured temperature.
        result = await self._attempt_syllabus_parse(
            prompt,
            temperature=temperature,
            json_mode=True,
            text=text,
        )
        if result is not None:
            return result

        logger.warning(
            "Syllabus JSON parse failed (temp=%s); retrying with lower "
            "temperature.",
            temperature,
        )

        # Attempt 2: JSON mode at a lower, more deterministic temperature.
        result = await self._attempt_syllabus_parse(
            prompt, temperature=0.1, json_mode=True, text=text
        )
        if result is not None:
            return result

        logger.warning(
            "Syllabus JSON parse failed (temp=0.1); retrying without "
            "JSON-mode constraint but with robust extraction."
        )

        # Attempt 3: No JSON-mode constraint - fall back to robust
        # extraction from a free-form response.
        result = await self._attempt_syllabus_parse(
            prompt, temperature=0.1, json_mode=False, text=text
        )
        if result is not None:
            return result

        return None

    async def _attempt_syllabus_parse(
        self,
        prompt: ChatPromptTemplate,
        temperature: float,
        json_mode: bool,
        text: str = "",
        max_retries: int = 3,
    ) -> Optional[dict]:
        """Try a single syllabus-parse attempt with retry on rate-limit errors.

        Returns the validated, parsed dict on success, or ``None`` on
        any failure so the caller can fall back to another strategy.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(max_retries):
            try:
                model = self._get_model(
                    temperature=temperature, json_mode=json_mode
                )
                chain = prompt | model | self.parser
                result = await chain.ainvoke({"text": text})

                cleaned = self._extract_json(result)
                data = json.loads(cleaned)
                data = self._normalize_syllabus_data(data)
                data = self._validate_syllabus_data(data)

                if not data.get("subjects"):
                    raise ValueError("Parsed syllabus contains no subjects")

                return data

            except RuntimeError:
                # Configuration errors (e.g. missing/invalid API key) are not
                # transient - retry will not help, so let them propagate.
                raise
            except _OversizedRequestError:
                # The request is too large for the model.  Do NOT retry —
                # return None so the caller can split or reduce the chunk.
                logger.warning(
                    "Request too large for model (attempt %d/%d); "
                    "caller should split input",
                    attempt + 1,
                    max_retries,
                )
                return None
            except Exception as exc:
                last_exc = exc
                exc_str = str(exc).lower()
                is_rate_limit = (
                    "429" in exc_str
                    or ("rate" in exc_str and "limit" in exc_str)
                )
                is_oversized = (
                    "413" in exc_str
                    or "request too large" in exc_str
                    or "requested" in exc_str and "exceed" in exc_str
                    or "request body too large" in exc_str
                )
                if is_oversized:
                    logger.warning(
                        "Request too large for model (attempt %d/%d); "
                        "caller should split input",
                        attempt + 1,
                        max_retries,
                    )
                    return None
                if is_rate_limit and attempt < max_retries - 1:
                    wait = 2 ** attempt * 5  # 5s, 10s, 20s
                    logger.warning(
                        "Rate limited on syllabus parse (attempt %d/%d), "
                        "retrying in %ds...",
                        attempt + 1,
                        max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.warning(
                        "Syllabus parse attempt failed "
                        "(temperature=%s, json_mode=%s): %s",
                        temperature,
                        json_mode,
                        exc,
                    )
                    return None

        logger.warning(
            "Syllabus parse attempt failed after %d retries: %s",
            max_retries,
            last_exc,
        )
        return None

    @staticmethod
    def _normalize_syllabus_data(data: dict) -> dict:
        """Normalize LLM syllabus output so that structural quirks are
        coerced into the expected schema before validation.

        This handles common LLM mistakes such as returning subjects or
        chapters as plain strings, topics as a single string, missing
        optional fields, etc.  Only *obvious* structural fixes are made;
        no academic content is invented.

        Returns the normalized dict (mutated in place for efficiency).
        """
        subjects = data.get("subjects")
        if subjects is None:
            return data

        # --- subjects level ---
        if isinstance(subjects, dict):
            logger.debug("Normalized subjects from object to list")
            data["subjects"] = [subjects]
            subjects = data["subjects"]
        elif isinstance(subjects, str):
            logger.debug("Normalized subjects string to subject list")
            data["subjects"] = [{"name": subjects, "chapters": []}]
            subjects = data["subjects"]

        if not isinstance(subjects, list):
            return data

        for subj in subjects:
            # Each subject must be a dict with at least a 'name'.
            if isinstance(subj, str):
                idx = subjects.index(subj)
                logger.debug(
                    "Normalized subject string '%s' to subject object", subj
                )
                subjects[idx] = {"name": subj, "description": "", "chapters": []}
                subj = subjects[idx]

            if not isinstance(subj, dict):
                continue

            subj.setdefault("description", "")

            # --- chapters level ---
            chapters = subj.get("chapters")
            if chapters is None:
                subj["chapters"] = []
                continue
            if isinstance(chapters, dict):
                logger.debug(
                    "Normalized chapters object to list in subject '%s'",
                    subj.get("name"),
                )
                subj["chapters"] = [chapters]
                chapters = subj["chapters"]
            elif isinstance(chapters, str):
                logger.debug(
                    "Normalized chapters string to chapter list in subject '%s'",
                    subj.get("name"),
                )
                subj["chapters"] = [
                    {"name": chapters, "description": "", "topics": [], "estimated_hours": 0}
                ]
                chapters = subj["chapters"]

            if not isinstance(chapters, list):
                continue

            for k, chap in enumerate(chapters):
                if isinstance(chap, str):
                    logger.debug(
                        "Normalized chapter string '%s' to chapter object in subject '%s'",
                        chap,
                        subj.get("name"),
                    )
                    chapters[k] = {
                        "name": chap,
                        "description": "",
                        "topics": [],
                        "estimated_hours": 0,
                    }
                    chap = chapters[k]

                if not isinstance(chap, dict):
                    continue

                chap.setdefault("description", "")
                chap.setdefault("estimated_hours", 0)

                # Coerce estimated_hours from numeric string
                eh = chap.get("estimated_hours")
                if isinstance(eh, str):
                    m = re.search(r"\d+", eh)
                    chap["estimated_hours"] = int(m.group()) if m else 0

                # --- topics level ---
                topics = chap.get("topics")
                if topics is None:
                    chap["topics"] = []
                elif isinstance(topics, str):
                    logger.debug(
                        "Normalized topics string to topic list in chapter '%s'",
                        chap.get("name"),
                    )
                    chap["topics"] = [topics]
                elif isinstance(topics, dict):
                    # LLM may return {"name": "..."} or {"topic": "..."}
                    name_val = (
                        topics.get("name")
                        or topics.get("title")
                        or topics.get("topic")
                        or str(topics)
                    )
                    logger.debug(
                        "Normalized topics object to topic list in chapter '%s'",
                        chap.get("name"),
                    )
                    chap["topics"] = [name_val] if name_val else []
                elif isinstance(topics, list):
                    # Normalise each element: extract .name/.title/.topic
                    # from any dicts, coerce anything else to str.
                    normalised: List[str] = []
                    for t in topics:
                        if isinstance(t, dict):
                            val = (
                                t.get("name")
                                or t.get("title")
                                or t.get("topic")
                                or str(t)
                            )
                            if val:
                                normalised.append(str(val))
                        else:
                            normalised.append(str(t))
                    chap["topics"] = normalised

        return data

    @staticmethod
    def _validate_syllabus_data(data: Any) -> dict:
        """Validate the structure of parsed syllabus data.

        Returns the validated dict, or raises ``ValueError`` with a
        descriptive message when the structure is invalid.

        Normalization should already have been applied before calling
        this method; this validator catches anything that normalization
        could not safely recover.
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

    # ----------------------------------------------------------------
    # Syllabus chunking helpers
    # ----------------------------------------------------------------

    # Regex that matches structural headings at the start of a line.
    # Captures the heading text so we can use it for chunk boundaries.
    _HEADING_RE = re.compile(
        r"^[ \t]*"
        r"(?:Unit|Module|Chapter|Part|Week|Lecture|Section|Topic)"
        r"\s+\S+",
        re.IGNORECASE | re.MULTILINE,
    )

    @staticmethod
    def _split_syllabus_text(text: str, max_chars: int) -> List[str]:
        """Split syllabus *text* into chunks that each fit within *max_chars*.

        Splitting strategy:
        1. If the text already fits in one chunk, return it as-is.
        2. Try to split on structural headings (Unit 1, Module 2, …).
        3. If a single section still exceeds *max_chars*, split it on
           paragraph boundaries (blank lines).
        4. As a last resort, hard-split on sentence boundaries.

        No content is discarded — every character of *text* appears in
        exactly one output chunk (whitespace-only chunks are dropped).
        """
        if len(text) <= max_chars:
            return [text]

        # --- Step 1: split on structural headings ---
        chunks: List[str] = []
        last_end = 0
        for m in re.finditer(LLMService._HEADING_RE, text):
            if m.start() > last_end:
                section = text[last_end : m.start()].strip()
                if section:
                    chunks.append(section)
            last_end = m.start()
        tail = text[last_end:].strip()
        if tail:
            chunks.append(tail)

        # --- Step 2: sub-split oversized chunks on blank lines ---
        final: List[str] = []
        for chunk in chunks:
            if len(chunk) <= max_chars:
                final.append(chunk)
            else:
                final.extend(
                    LLMService._split_on_blank_lines(chunk, max_chars)
                )

        # --- Step 3: hard-split any remaining oversized chunks on sentences ---
        result: List[str] = []
        for chunk in final:
            if len(chunk) <= max_chars:
                result.append(chunk)
            else:
                result.extend(
                    LLMService._split_on_sentences(chunk, max_chars)
                )

        return result if result else [text[:max_chars]]

    @staticmethod
    def _split_on_blank_lines(text: str, max_chars: int) -> List[str]:
        """Split *text* on blank-line boundaries, keeping each paragraph
        together.  Paragraphs longer than *max_chars* are passed through
        to sentence-level splitting by the caller."""
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        current = ""
        for para in paragraphs:
            candidate = f"{current}\n\n{para}".strip() if current else para
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = para
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _split_on_sentences(text: str, max_chars: int) -> List[str]:
        """Last-resort split on sentence boundaries (`. ` or newline)."""
        sentences = re.split(r"(?<=[.!?])\s+|\n", text)
        chunks: List[str] = []
        current = ""
        for sent in sentences:
            candidate = f"{current} {sent}".strip() if current else sent
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks

    @staticmethod
    def _merge_syllabus_chunks(chunk_results: List[dict]) -> dict:
        """Merge multiple parsed syllabus chunk results into one structure.

        Each element of *chunk_results* is a dict with a ``"subjects"`` key
        containing a list of subject dicts.  Subjects whose ``"name"``
        matches (case-insensitive, stripped) are merged; otherwise they
        are appended in order.

        No content is invented — only the data returned by the LLM is used.
        """
        merged_subjects: List[dict] = []
        # index by normalised subject name for quick lookup
        name_index: Dict[str, int] = {}

        for chunk in chunk_results:
            for subj in chunk.get("subjects", []):
                if not isinstance(subj, dict):
                    continue
                raw_name = (subj.get("name") or "").strip()
                norm_name = raw_name.lower()
                if norm_name and norm_name in name_index:
                    # Merge into existing subject
                    idx = name_index[norm_name]
                    existing = merged_subjects[idx]
                    # Merge chapters by name
                    existing_chapters = {
                        (c.get("name") or "").strip().lower(): c
                        for c in existing.get("chapters", [])
                        if isinstance(c, dict)
                    }
                    for new_chap in subj.get("chapters", []):
                        if not isinstance(new_chap, dict):
                            continue
                        chap_key = (new_chap.get("name") or "").strip().lower()
                        if chap_key and chap_key in existing_chapters:
                            # Merge topics from duplicate chapter
                            ec = existing_chapters[chap_key]
                            old_topics = ec.get("topics") or []
                            new_topics = new_chap.get("topics") or []
                            seen = {t.lower() for t in old_topics if isinstance(t, str)}
                            for t in new_topics:
                                if isinstance(t, str) and t.lower() not in seen:
                                    old_topics.append(t)
                                    seen.add(t.lower())
                            ec["topics"] = old_topics
                            # Update estimated_hours (take the larger value)
                            ec["estimated_hours"] = max(
                                ec.get("estimated_hours", 0),
                                new_chap.get("estimated_hours", 0),
                            )
                        else:
                            existing.setdefault("chapters", []).append(new_chap)
                else:
                    # New subject
                    name_index[norm_name] = len(merged_subjects)
                    merged_subjects.append(subj)

        return {"subjects": merged_subjects}

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
