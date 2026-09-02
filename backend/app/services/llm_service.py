"""
LLM Service - handles AI language model interactions.

Supports Groq as the LLM provider.

The service is intentionally self-contained so changes here do not
require modifications to other application files.
"""

import asyncio
import json
import re
from collections import Counter
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

from app.core.config import settings
from app.core.logger import get_logger
from app.services.syllabus_structure import is_pseudo_unit_heading


logger = get_logger(__name__)


class _OversizedRequestError(Exception):
    """
    Raised when the LLM request exceeds the model's input size limit.

    This is not treated as a transient error. The caller should split the
    input into smaller pieces instead of retrying the same request.
    """

    pass


class _GenerationFailedError(Exception):
    """
    Raised when the LLM cannot produce a valid JSON object for a chunk.

    Covers Groq's ``json_validate_failed`` response (the model generated
    text that is not parseable JSON, e.g. after a repetition loop hit the
    output token cap) as well as Python-side repetition-loop detection.
    Retrying the same input rarely helps: the caller must reduce the
    chunk size and try again with smaller semantic units.
    """

    pass


class LLMService:
    """
    Service for interacting with the Groq LLM.

    The model is initialized lazily so the backend can start even when
    the API key is not configured.
    """

    # Used when the primary model's quota is exhausted (e.g. Groq's
    # tokens-per-day limit). Different models have independent TPD
    # buckets, so this keeps AI features working after heavy usage.
    FALLBACK_MODELS = ["qwen/qwen3.6-27b", "openai/gpt-oss-120b"]

    def __init__(self):
        self.model: Optional[ChatGroq] = None
        self.parser = StrOutputParser()
        self._model_cache_key: Optional[tuple] = None

    # ================================================================
    # MODEL
    # ================================================================

    def _get_model(
        self,
        temperature: float = 0.7,
        json_mode: bool = False,
        max_output_tokens: Optional[int] = None,
        model_name: Optional[str] = None,
    ) -> ChatGroq:
        model_name = model_name or settings.GROQ_MODEL
        cache_key = (temperature, json_mode, max_output_tokens, model_name)

        if self.model is None or cache_key != self._model_cache_key:
            api_key = getattr(settings, "GROQ_API_KEY", None)
            if not api_key or api_key.startswith("your_"):
                raise RuntimeError(
                    "GROQ_API_KEY is not configured. "
                    "Add it to your backend .env file before using AI features."
                )

            model_kwargs: Dict[str, Any] = {}
            if json_mode:
                model_kwargs["response_format"] = {"type": "json_object"}

            # Reasoning models (e.g. openai/gpt-oss-20b) spend output tokens
            # on hidden chain-of-thought, which can exhaust max_tokens before
            # any visible content is produced (finish_reason=length with an
            # empty message). Requesting low reasoning effort keeps the
            # visible JSON answer within budget.
            extra_params: Dict[str, Any] = {}
            lowered = model_name.lower()
            if "qwen" in lowered:
                extra_params["reasoning_effort"] = "none"
            elif any(marker in lowered for marker in ("gpt-oss", "deepseek-r1")):
                extra_params["reasoning_effort"] = "low"

            # Syllabus parsing reserves a smaller output budget
            # (GROQ_SYLLABUS_MAX_OUTPUT_TOKENS) so input + output always fit
            # inside the model's context window.
            self.model = ChatGroq(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                max_tokens=(
                    max_output_tokens
                    if max_output_tokens is not None
                    else settings.GROQ_MAX_TOKENS
                ),
                model_kwargs=model_kwargs,
                **extra_params,
            )
            self._model_cache_key = cache_key

        return self.model

    async def _ainvoke_text(
        self,
        messages: List[Any],
        temperature: float,
        json_mode: bool,
    ) -> str:
        """Invoke the model, falling back to alternate models when the
        primary model hits its rate limit (e.g. tokens-per-day cap).
        Returns the raw text output."""
        attempted_rate_limit = False
        candidates = [None] + [
            m for m in self.FALLBACK_MODELS if m != settings.GROQ_MODEL
        ]
        last_error: Optional[Exception] = None

        for idx, model_name in enumerate(candidates):
            try:
                model = self._get_model(
                    temperature=temperature,
                    json_mode=json_mode,
                    model_name=model_name,
                )
                chain = model | self.parser
                result = await chain.ainvoke(messages)
                self._remember_model(model_name)
                return result or ""
            except Exception as e:  # noqa: BLE001
                is_rate_limit = (
                    "rate_limit_exceeded" in str(e) or "429" in str(e)
                )
                if idx == 0 and not is_rate_limit:
                    # Primary model failing for a non-quota reason is a real
                    # error - don't mask it with fallbacks.
                    raise
                last_error = e
                attempted_rate_limit = True
                logger.warning(
                    "Model %s unavailable (%s); trying fallback...",
                    model_name or settings.GROQ_MODEL,
                    str(e)[:160],
                )
                continue

        raise last_error  # type: ignore[misc]

    def _remember_model(self, model_name: Optional[str]) -> None:
        """Track which model produced output for logging/debugging."""
        self.last_model_used = model_name or settings.GROQ_MODEL

    # ================================================================
    # JSON EXTRACTION
    # ================================================================

    @staticmethod
    def _extract_json(result: str) -> str:
        if not result:
            return result

        result = result.strip()

        if result.startswith("```json"):
            result = result[len("```json"):]
        elif result.startswith("```"):
            result = result[len("```"):]

        if result.endswith("```"):
            result = result[:-3]

        result = result.strip()

        try:
            json.loads(result)
            return result
        except (json.JSONDecodeError, ValueError):
            pass

        candidates = []
        brace_start = result.find("{")
        bracket_start = result.find("[")

        if brace_start != -1:
            candidates.append((brace_start, "{", "}"))
        if bracket_start != -1:
            candidates.append((bracket_start, "[", "]"))

        candidates.sort(key=lambda item: item[0])

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
                            candidate = result[start:i + 1]
                            try:
                                json.loads(candidate)
                                return candidate
                            except (json.JSONDecodeError, ValueError):
                                break

        object_match = re.search(r"\{.*\}", result, re.DOTALL)
        if object_match:
            candidate = object_match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except (json.JSONDecodeError, ValueError):
                pass

        array_match = re.search(r"\[.*\]", result, re.DOTALL)
        if array_match:
            candidate = array_match.group(0)
            try:
                json.loads(candidate)
                return candidate
            except (json.JSONDecodeError, ValueError):
                pass

        return result

    # ================================================================
    # BASIC GENERATION
    # ================================================================

    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
    ) -> str:
        model = self._get_model(temperature=temperature)
        response = await model.ainvoke(prompt)
        return response.content

    # ================================================================
    # CHAT COMPLETION
    # ================================================================

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
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

        response = await model.ainvoke(lc_messages)
        return response.content

    # ================================================================
    # SYLLABUS PARSING
    # ================================================================

    async def parse_syllabus_content(self, text: str) -> dict:
        if not text or not text.strip():
            logger.warning("Syllabus parsing received empty text.")
            return {"subjects": []}

        max_chars = getattr(settings, "GROQ_SYLLABUS_MAX_INPUT_CHARS", 1800)
        text = text.strip()

        if len(text) <= max_chars:
            logger.info("Syllabus parsing: %d chars, single-pass", len(text))
            return await self._parse_syllabus_piece(text)

        pieces = self._split_for_llm(text, max_chars)
        logger.info(
            "Syllabus parsing: %d chars exceeds "
            "GROQ_SYLLABUS_MAX_INPUT_CHARS=%d; split into %d pieces",
            len(text), max_chars, len(pieces),
        )

        piece_results: List[dict] = []
        min_interval = getattr(settings, "GROQ_SYLLABUS_MIN_INTERVAL_SECONDS", 1.0)
        for i, piece in enumerate(pieces, start=1):
            logger.info(
                "[PARSER] piece %d/%d original chars: %d",
                i, len(pieces), len(piece),
            )
            try:
                # Pace requests to stay within the Groq TPM rate limit.
                if i > 1 and min_interval > 0:
                    await asyncio.sleep(min_interval)

                piece_result = await self._parse_syllabus_piece(piece)
                if piece_result:
                    piece_results.append(piece_result)
            except Exception as exc:
                logger.exception(
                    "[PARSER] Failed to parse piece %d/%d: %s",
                    i, len(pieces), exc,
                )

        if not piece_results:
            logger.error("Syllabus parsing: no pieces produced results")
            return {"subjects": []}

        if len(piece_results) == 1:
            return piece_results[0]

        return self._merge_syllabus_chunks(piece_results)

    async def _parse_syllabus_piece(self, text: str) -> dict:
        # Concise, extraction-only prompt.  Long instruction lists push a
        # small model like allam-2-7b into verbose/hallucinated output and
        # repetition loops, and waste input tokens.  NOTE: literal JSON
        # braces below MUST stay doubled ({{ }}) - LangChain treats single
        # braces as f-string template variables.
        system_prompt = (
            "You are an information extraction system.\n"
            "Extract ONLY text explicitly present in <syllabus>.\n"
            "Do not explain. Do not summarize. Do not infer. Do not add "
            "anything from your own knowledge.\n"
            "Never repeat an item. When the input ends, stop immediately.\n\n"
            "Return ONLY this JSON object (no markdown fences):\n"
            '{{"subjects": [{{"name": "", "description": "", "chapters": '
            '[{{"name": "", "description": "", "topics": [], '
            '"estimated_hours": 0}}]}}]}}\n\n'
            "Rules:\n"
            "- A chapter exists ONLY for a line explicitly numbered as a "
            "unit/module/chapter/part/week in the input, e.g. \"Unit 2: "
            "Introduction to Computer\" or \"U3 The Computer System "
            "Hardware\". Copy that heading VERBATIM (including its number) "
            "as the chapter name.\n"
            "- Generic section headings such as \"Syllabus\", \"Course "
            "Contents\", \"Objectives\", \"Course Description\", "
            "\"References\", \"Textbooks\", \"Evaluation\", \"Bibliography\" "
            "or a bare \"Introduction\" are NOT chapters unless the input "
            "numbers them as a unit.\n"
            "- If the heading states hours like \"(3 Hrs.)\" or \"(4 "
            "Hours)\", set \"estimated_hours\" to that number and omit the "
            "hours from the chapter name. Otherwise \"estimated_hours\" "
            "must be 0.\n"
            "- List the items written under a heading verbatim in "
            "\"topics\", in the original order. Never add topics that are "
            "not written there.\n"
            '- "description" must be "" unless the input states one.\n'
            "- \"subjects\" name: use the course/programme title only if it "
            'appears in the input; otherwise use "".\n'
            "- Output nothing except the JSON object."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "<syllabus>\n{text}\n</syllabus>"),
            ]
        )

        temperature = 0.2

        max_chars = getattr(settings, "GROQ_SYLLABUS_MAX_INPUT_CHARS", 1800)
        max_output_tokens = getattr(
            settings, "GROQ_SYLLABUS_MAX_OUTPUT_TOKENS", 1024
        )

        logger.info(
            "[PARSER] total input characters: %d, configured max: %d",
            len(text), max_chars,
        )

        parsed = await self._parse_chunk_with_splitting(
            prompt=prompt,
            chunk=text,
            temperature=temperature,
            max_chars=max_chars,
            max_output_tokens=max_output_tokens,
        )

        if parsed is None:
            raise ValueError("Failed to parse syllabus content after all attempts")

        return parsed

    # ================================================================
    # LLM SPLITTING
    # ================================================================

    def _split_for_llm(self, text: str, max_chars: int) -> List[str]:
        return self._split_syllabus_text(text, max_chars)

    # ================================================================
    # PARSE CHUNK WITH OVERSIZE / GENERATION-FAILURE HANDLING
    # ================================================================

    # Hard bound on how deep recursive splitting may go.  With the budget
    # halving used below this can never be reached in practice, but it
    # guarantees the retry loop is bounded.
    MAX_SPLIT_DEPTH = 6

    def _log_failed_chunk(
        self, chunk: str, depth: int, reason: str,
    ) -> None:
        """Log diagnostics for a chunk that could not be parsed (K)."""
        chars_per_token = getattr(settings, "GROQ_SYLLABUS_CHARS_PER_TOKEN", 4)
        max_output_tokens = getattr(
            settings, "GROQ_SYLLABUS_MAX_OUTPUT_TOKENS", 1024
        )
        preview = chunk[:300].replace("\n", "\\n")
        logger.error(
            "[PARSER] giving up on chunk (%s): chars=%d ~tokens=%d depth=%d "
            "model=%s max_output_tokens=%d preview=%r",
            reason,
            len(chunk),
            max(1, len(chunk) // chars_per_token),
            depth,
            settings.GROQ_MODEL,
            max_output_tokens,
            preview,
        )

    async def _parse_chunk_with_splitting(
        self,
        prompt: ChatPromptTemplate,
        chunk: str,
        temperature: float,
        max_chars: int,
        depth: int = 0,
        max_output_tokens: Optional[int] = None,
    ) -> Optional[dict]:
        chars_per_token = getattr(settings, "GROQ_SYLLABUS_CHARS_PER_TOKEN", 4)
        est_tokens = max(1, len(chunk) // chars_per_token)

        logger.info(
            "[PARSER] sending subchunk chars=%d ~tokens=%d depth=%d",
            len(chunk), est_tokens, depth,
        )

        try:
            result = await self._parse_single_chunk(
                prompt=prompt, text=chunk, temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
            logger.info("[PARSER] received response for subchunk chars=%d", len(chunk))
            return result
        except (_OversizedRequestError, _GenerationFailedError) as exc:
            # Both errors mean "this chunk is too much for one request":
            # input too large, or the model failed to produce valid JSON
            # (typically after a repetition loop consumed the output
            # budget).  Retrying unchanged does not help — split smaller.
            logger.warning(
                "[PARSER] chunk of %d chars failed (%s); "
                "splitting into smaller pieces",
                len(chunk), type(exc).__name__,
            )

        min_chunk = getattr(settings, "GROQ_SYLLABUS_MIN_CHUNK_CHARS", 300)

        if depth >= self.MAX_SPLIT_DEPTH:
            self._log_failed_chunk(chunk, depth, "max split depth reached")
            return None

        # Do not shred syllabus structure below a sensible minimum size.
        if len(chunk.strip()) <= min_chunk:
            self._log_failed_chunk(chunk, depth, "chunk at/below minimum size")
            return None

        # Halve the budget relative to BOTH the configured limit and the
        # actual chunk length.  Using only max_chars//2 previously allowed
        # sub_max >= len(chunk) (e.g. a 694-char chunk with sub_max=900),
        # which made the splitter return the chunk unchanged and tripped
        # the no-progress guard.
        half = max(len(chunk) // 2, 1)
        if max_chars > 0:
            sub_max = min(max_chars // 2, half)
        else:
            sub_max = half
        if sub_max < min_chunk and half > min_chunk:
            sub_max = min_chunk
        # Absolute progress guarantee: strictly smaller than the chunk.
        if sub_max >= len(chunk):
            sub_max = half

        sub_chunks = self._split_syllabus_text(chunk, sub_max)
        logger.info(
            "[PARSER] split into %d subchunks (sub_max=%d)",
            len(sub_chunks), sub_max,
        )

        # Guard against infinite recursion: splitter must make progress.
        if len(sub_chunks) == 1 and len(sub_chunks[0]) >= len(chunk):
            logger.warning(
                "[PARSER] splitter made no progress on %d chars; "
                "forcing hard character split",
                len(chunk),
            )
            sub_chunks = self._hard_split(chunk, sub_max)

        piece_results: List[dict] = []
        for i, piece in enumerate(sub_chunks, start=1):
            logger.info(
                "[PARSER] subchunk %d/%d chars=%d",
                i, len(sub_chunks), len(piece),
            )
            parsed = await self._parse_chunk_with_splitting(
                prompt=prompt, chunk=piece, temperature=temperature,
                max_chars=sub_max, depth=depth + 1,
                max_output_tokens=max_output_tokens,
            )
            if parsed:
                piece_results.append(parsed)

        if not piece_results:
            return None
        if len(piece_results) == 1:
            return piece_results[0]
        return self._merge_syllabus_chunks(piece_results)

    # ================================================================
    # SINGLE CHUNK PARSING
    # ================================================================

    async def _parse_single_chunk(
        self,
        prompt: ChatPromptTemplate,
        text: str,
        temperature: float,
        max_output_tokens: Optional[int] = None,
    ) -> Optional[dict]:
        try:
            result = await self._attempt_syllabus_parse(
                prompt=prompt, temperature=temperature, json_mode=True,
                text=text, max_output_tokens=max_output_tokens,
            )
            if result is not None:
                return result

            logger.warning(
                "Syllabus JSON parse failed at temperature=%s. Retrying at 0.1.", temperature,
            )

            result = await self._attempt_syllabus_parse(
                prompt=prompt, temperature=0.1, json_mode=True,
                text=text, max_output_tokens=max_output_tokens,
            )
            if result is not None:
                return result

            logger.warning("Syllabus JSON parse failed in JSON mode. Retrying without.")

            result = await self._attempt_syllabus_parse(
                prompt=prompt, temperature=0.1, json_mode=False,
                text=text, max_output_tokens=max_output_tokens,
            )
            return result
        except _GenerationFailedError:
            # The model could not generate valid output for THIS chunk
            # (json_validate_failed / repetition loop).  Re-running the
            # same input in another mode almost always fails the same way;
            # let the caller reduce the chunk size instead.
            raise

    # ================================================================
    # ATTEMPT SYLLABUS PARSE
    # ================================================================

    async def _attempt_syllabus_parse(
        self,
        prompt: ChatPromptTemplate,
        temperature: float,
        json_mode: bool,
        text: str = "",
        max_retries: int = 3,
        max_output_tokens: Optional[int] = None,
    ) -> Optional[dict]:
        last_exc: Optional[Exception] = None
        max_output_tokens_effective = (
            max_output_tokens
            if max_output_tokens is not None
            else getattr(settings, "GROQ_SYLLABUS_MAX_OUTPUT_TOKENS", 1024)
        )

        for attempt in range(max_retries):
            try:
                model = self._get_model(
                    temperature=temperature,
                    json_mode=json_mode,
                    max_output_tokens=max_output_tokens,
                )
                chain = prompt | model | self.parser
                result = await chain.ainvoke({"text": text})

                cleaned = self._extract_json(result)
                data = json.loads(cleaned)

                # Detect degenerate output BEFORE normalization/dedup so a
                # repetition loop is treated as a generation failure and the
                # caller retries with a smaller chunk (instead of silently
                # truncating or deduplicating fabricated topics).
                if self._looks_like_repetition_loop(data):
                    raise _GenerationFailedError(
                        "repetition loop detected in model output"
                    )

                data = self._normalize_syllabus_data(data)
                data = self._validate_syllabus_data(data)

                if not data.get("subjects"):
                    raise ValueError("Parsed syllabus contains no subjects")

                for subj in data["subjects"]:
                    logger.info("[PARSER] Course: %r", subj.get("name"))
                    for chap in subj.get("chapters", []):
                        hours = chap.get("estimated_hours", 0)
                        logger.info(
                            "[PARSER] Unit: %r | Hours: %s",
                            chap.get("name"),
                            hours if hours else "not stated",
                        )
                        for topic in (chap.get("topics") or [])[:50]:
                            logger.info(
                                "[PARSER] Topic: %r (unit=%r)",
                                topic, chap.get("name"),
                            )

                return data

            except RuntimeError:
                raise

            except (_OversizedRequestError, _GenerationFailedError):
                raise

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
                    or ("requested" in exc_str and "exceed" in exc_str)
                    or "request body too large" in exc_str
                    or "context length" in exc_str
                    or "maximum context" in exc_str
                )

                # Groq JSON mode returns 400 json_validate_failed when the
                # raw completion is not valid JSON — typically because a
                # repetition loop consumed the output budget and the JSON
                # was cut off mid-object.  Retrying the same request does
                # not help; force the caller to use a smaller chunk.
                is_generation_failure = (
                    "json_validate_failed" in exc_str
                    or "failed_generation" in exc_str
                    or "failed to generate json" in exc_str
                )

                if is_oversized:
                    logger.warning("Request too large for model. Caller will split.")
                    raise _OversizedRequestError(str(exc)) from exc

                if is_generation_failure:
                    logger.warning(
                        "Model failed to generate valid JSON "
                        "(json_validate_failed). Caller will split."
                    )
                    raise _GenerationFailedError(str(exc)) from exc

                if is_rate_limit and attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)
                    logger.warning(
                        "Rate limited (attempt %d/%d). Retrying in %ds...",
                        attempt + 1, max_retries, wait,
                    )
                    await asyncio.sleep(wait)
                    continue

                chars_per_token = getattr(
                    settings, "GROQ_SYLLABUS_CHARS_PER_TOKEN", 4
                )
                logger.warning(
                    "Syllabus parse failed (temp=%s, json=%s): %s | "
                    "chunk_chars=%d ~tokens=%d model=%s max_tokens=%d",
                    temperature, json_mode, exc,
                    len(text), max(1, len(text) // chars_per_token),
                    settings.GROQ_MODEL,
                    max_output_tokens_effective,
                )
                return None

        logger.warning(
            "Syllabus parse failed after %d retries: %s | chunk_chars=%d "
            "model=%s max_tokens=%d",
            max_retries, last_exc, len(text),
            settings.GROQ_MODEL, max_output_tokens_effective,
        )
        return None

    @staticmethod
    def _looks_like_repetition_loop(data: Any) -> bool:
        """
        Detect degenerate repetition-loop output on the RAW LLM response.

        Runs before normalization/dedup so duplicates are still visible.
        A chapter is degenerate when its topic list shows heavy duplication:

        - any single topic repeated >= 4 times, or
        - >= 8 entries with less than 60%% unique values.

        Legitimate syllabi essentially never repeat the exact same topic
        name, while large real chapters (60+ unique topics) pass untouched.
        """
        if not isinstance(data, dict):
            return False

        subjects = data.get("subjects")
        if not isinstance(subjects, list):
            return False

        for subj in subjects:
            if not isinstance(subj, dict):
                continue
            chapters = subj.get("chapters")
            if not isinstance(chapters, list):
                continue
            for chap in chapters:
                if not isinstance(chap, dict):
                    continue
                topics = chap.get("topics")
                if not isinstance(topics, list):
                    continue

                items = [
                    str(t).strip().casefold()
                    for t in topics
                    if str(t).strip()
                ]
                total = len(items)
                if total < 8:
                    continue

                counts = Counter(items)
                most_common_count = max(counts.values())
                unique_ratio = len(counts) / total

                if most_common_count >= 4 or unique_ratio <= 0.6:
                    logger.warning(
                        "[PARSER] Repetition loop detected in chapter '%s': "
                        "%d topics, %d unique (ratio %.2f), "
                        "most common repeated %d times",
                        chap.get("name", "?"),
                        total, len(counts), unique_ratio, most_common_count,
                    )
                    return True

        return False

    # ================================================================
    # NORMALIZE SYLLABUS
    # ================================================================

    @staticmethod
    def _normalize_syllabus_data(data: dict) -> dict:
        if not isinstance(data, dict):
            return data

        if data.get("subjects") is None:
            for alt in ("syllabus", "units", "courses", "subjects_data"):
                value = data.get(alt)
                if isinstance(value, (list, dict)):
                    logger.debug("Normalized top-level '%s' to 'subjects'", alt)
                    data["subjects"] = data.pop(alt)
                    break

        subjects = data.get("subjects")
        if subjects is None:
            return data

        if isinstance(subjects, dict):
            data["subjects"] = [subjects]
            subjects = data["subjects"]
        elif isinstance(subjects, str):
            data["subjects"] = [{"name": subjects, "description": "", "chapters": []}]
            subjects = data["subjects"]

        if not isinstance(subjects, list):
            return data

        for subject_index, subj in enumerate(subjects):
            if isinstance(subj, str):
                subjects[subject_index] = {"name": subj, "description": "", "chapters": []}
                subj = subjects[subject_index]

            if not isinstance(subj, dict):
                continue

            if not subj.get("name"):
                for name_key in ("subject_name", "unit_name", "title"):
                    if subj.get(name_key):
                        subj["name"] = subj[name_key]
                        break

            subj.setdefault("description", "")

            if not subj.get("chapters") and isinstance(subj.get("units"), list):
                logger.debug("Normalized 'units' to 'chapters' in subject '%s'", subj.get("name"))
                subj["chapters"] = subj.pop("units")

            chapters = subj.get("chapters")
            if chapters is None:
                subj["chapters"] = []
                continue
            if isinstance(chapters, dict):
                subj["chapters"] = [chapters]
                chapters = subj["chapters"]
            elif isinstance(chapters, str):
                subj["chapters"] = [
                    {"name": chapters, "description": "", "topics": [], "estimated_hours": 0}
                ]
                chapters = subj["chapters"]

            if not isinstance(chapters, list):
                continue

            for chapter_index, chap in enumerate(chapters):
                if isinstance(chap, str):
                    chapters[chapter_index] = {
                        "name": chap, "description": "", "topics": [], "estimated_hours": 0,
                    }
                    chap = chapters[chapter_index]

                if not isinstance(chap, dict):
                    continue

                if not chap.get("name"):
                    for name_key in ("chapter_name", "unit_name", "unit", "title"):
                        if chap.get(name_key):
                            chap["name"] = chap[name_key]
                            break

                # If still no name, try to recover from the subject context.
                # Use subject name + chapter index as a fallback only when
                # the chapter has meaningful topics (avoid inventing names
                # for empty/degenerate chapter objects).
                if not chap.get("name"):
                    chap_topics = chap.get("topics") or []
                    if isinstance(chap_topics, list) and len(chap_topics) > 0:
                        subj_name = subj.get("name", "Subject")
                        chap["name"] = f"{subj_name} - Chapter {chapter_index + 1}"
                        logger.debug(
                            "[PARSER] Inferred chapter name '%s' from context "
                            "(subject '%s', index %d)",
                            chap["name"], subj_name, chapter_index,
                        )
                    else:
                        # Chapter has no name AND no topics — drop it entirely
                        # rather than passing a malformed object to the validator.
                        logger.warning(
                            "[PARSER] Dropping chapter at index %d in subject "
                            "'%s': no name and no topics",
                            chapter_index, subj.get("name", "?"),
                        )
                        chapters[chapter_index] = None  # type: ignore[assignment]
                        continue

                chap.setdefault("description", "")
                chap.setdefault("estimated_hours", 0)

                estimated_hours = chap.get("estimated_hours")
                if isinstance(estimated_hours, str):
                    match = re.search(r"\d+", estimated_hours)
                    chap["estimated_hours"] = int(match.group()) if match else 0
                elif not isinstance(estimated_hours, (int, float)):
                    chap["estimated_hours"] = 0

                topics = chap.get("topics")
                if topics is None:
                    chap["topics"] = []
                elif isinstance(topics, str):
                    chap["topics"] = [topics]
                elif isinstance(topics, dict):
                    topic_name = (
                        topics.get("name")
                        or topics.get("title")
                        or topics.get("topic")
                        or topics.get("topic_name")
                    )
                    chap["topics"] = [str(topic_name)] if topic_name else []
                elif isinstance(topics, list):
                    normalized_topics: List[str] = []
                    for topic in topics:
                        if isinstance(topic, dict):
                            value = (
                                topic.get("name")
                                or topic.get("title")
                                or topic.get("topic")
                                or topic.get("topic_name")
                            )
                            if value:
                                normalized_topics.append(str(value))
                        elif topic is not None:
                            normalized_topics.append(str(topic))
                    chap["topics"] = normalized_topics
                else:
                    chap["topics"] = []

                raw_topics = chap.get("topics", [])
                seen: set = set()
                unique_topics: List[str] = []
                for topic in raw_topics:
                    topic_str = str(topic).strip()
                    if not topic_str:
                        continue
                    topic_key = topic_str.casefold()
                    if topic_key not in seen:
                        seen.add(topic_key)
                        unique_topics.append(topic_str)
                chap["topics"] = unique_topics

            # Remove any chapters that were set to None (dropped for being
            # completely empty / nameless with no recoverable context).
            subj["chapters"] = [c for c in chapters if c is not None]

        return data

    # ================================================================
    # VALIDATE SYLLABUS
    # ================================================================

    @staticmethod
    def _validate_syllabus_data(data: Any) -> dict:
        if not isinstance(data, dict):
            raise ValueError(
                f"Expected JSON object at top level, got {type(data).__name__}"
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

            valid_chapters = []
            seen_chapter_keys = set()
            for j, chap in enumerate(chapters):
                if not isinstance(chap, dict):
                    logger.warning(
                        "[PARSER] Skipping non-dict chapter at index %d "
                        "in subject '%s'",
                        j, subj.get("name"),
                    )
                    continue
                if not chap.get("name"):
                    logger.warning(
                        "[PARSER] Skipping chapter at index %d in subject "
                        "'%s': still missing 'name' after normalization",
                        j, subj.get("name"),
                    )
                    continue

                # Reject generic section headings ("Syllabus", "Objectives",
                # ...) that the model wrongly promoted to units.
                if is_pseudo_unit_heading(chap.get("name", "")):
                    logger.warning(
                        "[PARSER] Rejected pseudo-unit chapter '%s' in "
                        "subject '%s': not defined as a unit in the source",
                        chap.get("name"), subj.get("name"),
                    )
                    continue

                # Drop duplicate chapters (case-insensitive), first wins,
                # preserving original ordering.
                chapter_key = str(chap["name"]).strip().casefold()
                if chapter_key in seen_chapter_keys:
                    logger.warning(
                        "[PARSER] Dropping duplicate chapter '%s' in "
                        "subject '%s'", chap["name"], subj.get("name"),
                    )
                    continue
                seen_chapter_keys.add(chapter_key)

                topics = chap.get("topics")
                if topics is not None and not isinstance(topics, list):
                    logger.warning(
                        "[PARSER] Chapter '%s' topics is not a list (got %s); "
                        "replacing with empty list",
                        chap.get("name"), type(topics).__name__,
                    )
                    chap["topics"] = []

                valid_chapters.append(chap)

            subj["chapters"] = valid_chapters

        return data

    # ================================================================
    # SYLLABUS SPLITTING
    # ================================================================
    # Heading lines such as "Unit 1:", "Unit 1. Introduction",
    # "Module 2 - Cloud", "Chapter 3: ...".  Anchored to the start of a
    # line so mid-sentence words like "part" never match.
    _HEADING_RE = re.compile(
        r"(?:^|(?<=\n))\s*"
        r"(?:Unit|Module|Chapter|Part|Week|Lecture|Section)"
        r"\s+\S+.*$",
        re.IGNORECASE | re.MULTILINE,
    )

    @staticmethod
    def _split_syllabus_text(text: str, max_chars: int) -> List[str]:
        """
        Reliably split syllabus text into chunks no larger than max_chars.

        The important rule here is:
        if text is larger than max_chars, this function MUST return
        at least two smaller chunks.
        """

        if not text or not text.strip():
            return [""]

        text = text.strip()

        if max_chars <= 0:
            return [text]

        if len(text) <= max_chars:
            return [text]

        chunks: List[str] = []
        position = 0
        text_length = len(text)

        # Overlap duplicates content across adjacent chunks, which both
        # wastes output tokens and produces repeated topics; splitting at
        # line boundaries already avoids cutting words in half, so the
        # default is zero (still configurable).
        overlap = min(
            getattr(settings, "GROQ_SYLLABUS_CHUNK_OVERLAP", 0),
            max_chars // 10,
        )

        while position < text_length:
            end = min(position + max_chars, text_length)

            # Try to split at a boundary that keeps a unit heading
            # together with its content.
            if end < text_length:
                window = text[position:end]
                heading_cut = -1
                for match in LLMService._HEADING_RE.finditer(window):
                    # Relative offset: only cut at a heading when enough
                    # content precedes it IN THIS CHUNK.  A heading at the
                    # very start of the window must never trigger a cut
                    # (that would produce a zero-length chunk and strand
                    # the heading's own body in the next one).
                    if match.start() > max_chars // 3:
                        heading_cut = match.start()

                newline_pos = text.rfind("\n", position, end)

                if heading_cut >= 0:
                    end = position + heading_cut
                elif newline_pos > position + max_chars // 2:
                    end = newline_pos
                else:
                    # If no useful newline, split at whitespace.
                    space_pos = text.rfind(" ", position, end)
                    if space_pos > position + max_chars // 2:
                        end = space_pos

            # Absolute safety: ALWAYS consume characters.
            if end <= position:
                end = min(position + max_chars, text_length)

            chunk = text[position:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            next_position = end - overlap

            # GUARANTEE progress.
            if next_position <= position:
                next_position = end

            position = next_position

        # Final safety check.
        if len(chunks) == 1 and len(chunks[0]) >= len(text):
            midpoint = len(text) // 2
            return [
                text[:midpoint].strip(),
                text[midpoint:].strip(),
            ]

        return [chunk for chunk in chunks if chunk]

    @staticmethod
    def _hard_split(
        text: str, max_chars: int, overlap: Optional[int] = None,
    ) -> List[str]:
        if len(text) <= max_chars:
            return [text]

        if overlap is None:
            overlap = getattr(settings, "GROQ_SYLLABUS_CHUNK_OVERLAP", 100)

        overlap = max(0, min(overlap, max_chars // 4))

        chunks: List[str] = []
        n = len(text)
        position = 0

        while position < n:
            end = min(position + max_chars, n)

            if end < n:
                search_start = position + max_chars // 2
                whitespace = text.rfind(" ", search_start, end)
                if whitespace > position:
                    end = whitespace

            chunk = text[position:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= n:
                break

            next_position = end - overlap
            if next_position <= position:
                next_position = end
            position = next_position

        return chunks

    @staticmethod
    def _split_on_blank_lines(text: str, max_chars: int) -> List[str]:
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: List[str] = []
        current = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if not current:
                current = paragraph
                continue

            candidate = current + "\n\n" + paragraph
            if len(candidate) <= max_chars:
                current = candidate
            else:
                chunks.append(current)
                current = paragraph

        if current:
            chunks.append(current)

        return chunks

    @staticmethod
    def _split_on_sentences(text: str, max_chars: int) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        chunks: List[str] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if not current:
                current = sentence
                continue

            candidate = current + " " + sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                chunks.append(current)
                current = sentence

        if current:
            chunks.append(current)

        return chunks

    # ================================================================
    # MERGE SYLLABUS CHUNKS
    # ================================================================

    @staticmethod
    def _merge_syllabus_chunks(chunk_results: List[dict]) -> dict:
        merged_subjects: List[dict] = []
        subject_index: Dict[str, int] = {}

        for chunk in chunk_results:
            if not isinstance(chunk, dict):
                continue

            subjects = chunk.get("subjects", [])
            if not isinstance(subjects, list):
                continue

            for subject in subjects:
                if not isinstance(subject, dict):
                    continue

                subject_name = str(subject.get("name", "")).strip()
                if not subject_name:
                    continue

                subject_key = subject_name.casefold()

                if subject_key not in subject_index:
                    new_subject = dict(subject)
                    new_subject.setdefault("chapters", [])
                    subject_index[subject_key] = len(merged_subjects)
                    merged_subjects.append(new_subject)

                existing_subject = merged_subjects[subject_index[subject_key]]
                existing_chapters: Dict[str, dict] = {}

                for chapter in existing_subject.get("chapters", []):
                    if not isinstance(chapter, dict):
                        continue
                    chapter_name = str(chapter.get("name", "")).strip()
                    if chapter_name:
                        existing_chapters[chapter_name.casefold()] = chapter

                for new_chapter in subject.get("chapters", []):
                    if not isinstance(new_chapter, dict):
                        continue

                    chapter_name = str(new_chapter.get("name", "")).strip()
                    if not chapter_name:
                        continue

                    chapter_key = chapter_name.casefold()

                    if chapter_key in existing_chapters:
                        existing_chapter = existing_chapters[chapter_key]

                        old_topics = existing_chapter.get("topics", []) or []
                        new_topics = new_chapter.get("topics", []) or []
                        seen_topics = {
                            str(t).casefold() for t in old_topics if t
                        }

                        for topic in new_topics:
                            topic_str = str(topic).strip()
                            if not topic_str:
                                continue
                            topic_key = topic_str.casefold()
                            if topic_key not in seen_topics:
                                old_topics.append(topic_str)
                                seen_topics.add(topic_key)

                        existing_chapter["topics"] = old_topics

                        old_hours = existing_chapter.get("estimated_hours", 0)
                        new_hours = new_chapter.get("estimated_hours", 0)
                        try:
                            existing_chapter["estimated_hours"] = max(
                                float(old_hours), float(new_hours),
                            )
                        except (TypeError, ValueError):
                            existing_chapter["estimated_hours"] = 0

                        continue

                    chapter_copy = dict(new_chapter)
                    chapter_copy.setdefault("topics", [])
                    existing_subject.setdefault("chapters", []).append(chapter_copy)
                    existing_chapters[chapter_key] = chapter_copy

        for subject in merged_subjects:
            for chapter in subject.get("chapters", []):
                hours = chapter.get("estimated_hours", 0)
                if isinstance(hours, float) and hours.is_integer():
                    chapter["estimated_hours"] = int(hours)

        return {"subjects": merged_subjects}

    # ================================================================
    # QUIZ GENERATION
    # ================================================================

    async def generate_quiz_questions(
        self,
        content: str,
        num_questions: int = 10,
        difficulty: str = "medium",
        topics: Optional[List[str]] = None,
        previous_questions: Optional[List[str]] = None,
        subject: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate MCQs grounded in the provided syllabus topics and
        curriculum content. Returns validated questions whose ``correct_answer``
        is the verbatim text of the correct option."""
        topics = topics or []
        previous_questions = previous_questions or []

        system_prompt = """
You are an expert educational exam and quiz generator for Mentora - AI Learning Companion.

Your task is to generate high-quality, academically sound multiple-choice questions (MCQs) that evaluate a student's understanding of the subjects, chapters, and topics defined in their syllabus.

RULES:
- Questions must strictly pertain to the curriculum topics and academic domain specified in the syllabus.
- Do NOT generate questions on unrelated subjects or domains outside the syllabus scope.
- Generate questions testing conceptual understanding, application of principles, technical terminology, and problem solving based on the syllabus.
- Each question must have exactly four distinct options.
- Exactly ONE option must be correct.
- "correct_answer" MUST be the verbatim text of the correct option - never a letter like "A" or "B".
- Every question must include a clear, educational "explanation" explaining why the correct answer is right and clarifying key concepts.
- Provide plausible distractors that test common student misconceptions (avoid trivially obvious wrong answers).
- Keep each question focused on ONE clear concept.
- Do NOT repeat any previously asked questions.

Return ONLY a valid JSON array:

[
  {
    "question_text": "...?",
    "options": ["option1", "option2", "option3", "option4"],
    "correct_answer": "<verbatim text of the correct option>",
    "explanation": "...",
    "difficulty": "easy|medium|hard"
  }
]
"""

        human_parts = []
        if subject:
            human_parts.append(f"Subject / Course: {subject}")
        if topics:
            human_parts.append(
                "Focus topics from syllabus:\n" + "\n".join(f"- {t}" for t in topics)
            )
        if previous_questions:
            shown = "\n".join(f"- {q}" for q in previous_questions[:50])
            human_parts.append(
                "Previously asked questions (do NOT repeat them):\n" + shown
            )
        human_parts.append(
            f"Generate {num_questions} multiple-choice questions "
            f"(target difficulty: {difficulty})."
        )
        if content and content.strip() and content.strip() != "(no content retrieved)":
            human_parts.append(
                "Syllabus Curriculum Context:\n"
                + content
            )
        elif not topics and not subject:
            human_parts.append(
                "Generate academic quiz questions for the curriculum."
            )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n\n".join(human_parts)),
        ]

        last_result: str = ""
        for attempt in range(2):
            result = await self._ainvoke_text(messages, temperature=0.4, json_mode=True)
            last_result = result or ""

            try:
                cleaned = self._extract_json(last_result)
                data = json.loads(cleaned)
                questions = self._validate_quiz_questions(
                    data, num_questions=num_questions, difficulty=difficulty
                )
                if questions:
                    return questions
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            logger.warning(
                "Quiz generation attempt %d returned no valid questions. "
                "Raw output (first 500 chars): %s",
                attempt + 1,
                last_result[:500],
            )

        return []

    @staticmethod
    def _validate_quiz_questions(
        data: Any,
        num_questions: int,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        """Normalize and validate raw LLM quiz output."""
        allowed_difficulties = {"easy", "medium", "hard"}
        raw_questions = data if isinstance(data, list) else (
            data.get("questions") if isinstance(data, dict) else None
        )
        if not isinstance(raw_questions, list):
            return []

        seen = set()
        validated: List[Dict[str, Any]] = []

        for raw in raw_questions:
            if not isinstance(raw, dict):
                continue
            question_text = str(raw.get("question_text") or "").strip()
            options_raw = raw.get("options")
            if not question_text or not isinstance(options_raw, list):
                continue

            options = [str(o).strip() for o in options_raw if str(o).strip()]
            if len(options) < 2:
                continue
            options = options[:4]

            correct = str(raw.get("correct_answer") or "").strip()
            if correct not in options:
                # LLM returned a letter/index instead of the option text.
                if len(correct) <= 2 and correct.isalpha():
                    idx = ord(correct.upper()) - ord("A")
                    if 0 <= idx < len(options):
                        correct = options[idx]
                else:
                    # fuzzy: find the option containing the answer text
                    match = next(
                        (o for o in options if correct.lower() in o.lower()), ""
                    )
                    correct = match or options[0]

            key = question_text.lower()
            if key in seen:
                continue
            seen.add(key)

            q_difficulty = str(raw.get("difficulty") or difficulty).strip().lower()
            if q_difficulty not in allowed_difficulties:
                q_difficulty = "medium"

            validated.append({
                "question_text": question_text,
                "options": options,
                "correct_answer": correct,
                "explanation": str(raw.get("explanation") or "").strip(),
                "difficulty": q_difficulty,
            })

        return validated[:num_questions]

    # ================================================================
    # FLASHCARDS
    # ================================================================

    async def generate_flashcards(
        self,
        retrieved_content: str,
        subject: str = "",
        unit: str = "",
        topics: Optional[List[str]] = None,
        student_level: str = "Bachelor",
        weak_topics: Optional[List[str]] = None,
        num_cards: Optional[int] = None,
        previous_questions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Flashcard Generation Engine.

        Generates exam-oriented flashcards strictly from the syllabus /
        RAG-retrieved content, with a balanced mix of card types and a
        30/50/20 easy/medium/hard difficulty distribution.
        """
        topics = topics or []
        weak_topics = weak_topics or []
        previous_questions = previous_questions or []

        if not num_cards:
            # Small topic -> 5, normal -> 10, large -> 15
            content_len = len(retrieved_content or "")
            if content_len < 1500:
                num_cards = 5
            elif content_len < 6000:
                num_cards = 10
            else:
                num_cards = 15

        system_prompt = """
You are the Flashcard Generation Engine for Mentora - AI Learning Companion.

Generate high-quality, exam-oriented flashcards strictly from the student's
syllabus and retrieved study content.

CORE RULES:
- Generate flashcards ONLY from the provided syllabus and retrieved content.
- Do NOT introduce unrelated concepts.
- Do NOT generate generic textbook questions that are not supported by the content.
- If the retrieved content is insufficient for a reliable flashcard, do not
  invent information: return fewer flashcards instead.
- The retrieved content is the primary source of truth. If it conflicts with
  your general knowledge, prioritize the retrieved content.
- Do not hallucinate missing syllabus topics.

FLASHCARD TYPES (use a balanced combination):
definition, concept, explanation, comparison, process, example,
application, exam, recall, higher_order

Avoid generating too many simple definition cards.

DIFFICULTY DISTRIBUTION per batch:
- 30% easy   : basic definitions and direct recall
- 50% medium : conceptual understanding, comparisons, explanations, applications
- 20% hard   : reasoning, scenario-based questions, relationships between concepts

QUALITY RULES - every flashcard must:
- Focus on ONE concept.
- Have a clear, unambiguous question.
- Have a concise but complete answer (usually 1-5 sentences; use bullet
  points when listing multiple items).
- Be understandable without extra context, in simple language.
- Preserve important technical terminology.
- Include formulas, steps, syntax, examples or key properties when they are
  present in the source material.
- Never duplicate another question.
For comparison answers use a structured format:
X:
- ...
Y:
- ...

OUTPUT FORMAT - return ONLY valid JSON with this exact structure:
{
  "subject": "...",
  "unit": "...",
  "topic": "...",
  "flashcards": [
    {
      "id": 1,
      "question": "...",
      "answer": "...",
      "type": "definition",
      "difficulty": "easy",
      "topic": "..."
    }
  ]
}

Every flashcard MUST contain: id, question, answer, type, difficulty, topic.
Allowed types: definition, concept, explanation, comparison, process,
example, application, exam, recall, higher_order.
Allowed difficulties: easy, medium, hard.

Before returning, verify: valid JSON, no duplicate questions, no
hallucinated information, correct type/difficulty labels, answers supported
by the retrieved content. Return ONLY the JSON object.
"""

        human_parts = [f"Subject: {subject or 'Not specified'}"]
        if unit:
            human_parts.append(f"Unit: {unit}")
        if topics:
            human_parts.append("Topics:\n" + "\n".join(f"- {t}" for t in topics))
        if weak_topics:
            human_parts.append(
                "Weak Topics (prioritize these with more conceptual, application "
                "and exam-oriented cards):\n"
                + "\n".join(f"- {t}" for t in weak_topics)
            )
        if previous_questions:
            shown = "\n".join(f"- {q}" for q in previous_questions[:50])
            human_parts.append(
                "Previously generated flashcard questions (do NOT repeat them):\n" + shown
            )
        human_parts.append(f"Number of Flashcards: {num_cards}")
        human_parts.append(f"Student Level: {student_level}")
        human_parts.append(
            "Retrieved Content (primary source of truth):\n"
            + (retrieved_content or "(no content retrieved)")
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="\n\n".join(human_parts)),
        ]

        last_result: str = ""
        for attempt in range(2):
            result = await self._ainvoke_text(messages, temperature=0.3, json_mode=True)
            last_result = result or ""

            try:
                cleaned = self._extract_json(last_result)
                data = json.loads(cleaned)
                cards = self._validate_flashcards(
                    data, topics=topics, unit=unit, subject=subject, max_cards=num_cards
                )
                if cards:
                    return {
                        "subject": subject or data.get("subject", ""),
                        "unit": unit or data.get("unit", ""),
                        "topic": data.get("topic") or (topics[0] if topics else ""),
                        "flashcards": cards,
                    }
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            logger.warning(
                "Flashcard generation attempt %d returned no valid cards. "
                "Raw output (first 500 chars): %s",
                attempt + 1,
                last_result[:500],
            )

        return {"subject": subject, "unit": unit, "topic": "", "flashcards": []}

    @staticmethod
    def _validate_flashcards(
        data: Any,
        topics: List[str],
        unit: str,
        subject: str,
        max_cards: Optional[int],
    ) -> List[Dict[str, Any]]:
        """Normalize and validate raw LLM flashcard output."""
        allowed_types = {
            "definition", "concept", "explanation", "comparison", "process",
            "example", "application", "exam", "recall", "higher_order",
        }
        allowed_difficulties = {"easy", "medium", "hard"}

        if isinstance(data, list):
            raw_cards = data
        elif isinstance(data, dict):
            raw_cards = data.get("flashcards")
            if not isinstance(raw_cards, list):
                return []
        else:
            return []

        fallback_topic = topics[0] if topics else ""
        seen_questions = set()
        validated: List[Dict[str, Any]] = []

        for raw in raw_cards:
            if not isinstance(raw, dict):
                continue
            question = str(raw.get("question") or "").strip()
            answer = str(raw.get("answer") or raw.get("back") or "").strip()
            if not question or not answer:
                continue

            key = question.lower()
            if key in seen_questions:
                continue
            seen_questions.add(key)

            card_type = str(raw.get("type") or "concept").strip().lower()
            if card_type not in allowed_types:
                card_type = "concept"

            difficulty = str(raw.get("difficulty") or "medium").strip().lower()
            if difficulty not in allowed_difficulties:
                difficulty = "medium"

            validated.append({
                "question": question,
                "answer": answer,
                "type": card_type,
                "difficulty": difficulty,
                "topic": str(raw.get("topic") or fallback_topic).strip(),
            })

        if max_cards:
            validated = validated[:max_cards]

        for i, card in enumerate(validated, start=1):
            card["id"] = i

        return validated

    # ================================================================
    # STUDY PLAN
    # ================================================================

    async def generate_study_plan(
        self,
        syllabus_data: dict,
        start_date: str,
        end_date: Optional[str] = None,
    ) -> dict:
        system_prompt = """
You are an expert educational study planner.

Create a detailed study plan based ONLY on the topics and chapters in the supplied syllabus.

Rules:
- Cover every unit/chapter from the syllabus.
- Distribute tasks across the available date range.
- Each task must study ONE specific topic or chapter from the syllabus.
- Do NOT invent topics that are not in the syllabus.

Return ONLY valid JSON with this exact structure:

{{
  "summary": "Brief overview of the plan",
  "tasks": [
    {{
      "title": "Study [specific topic name from syllabus]",
      "description": "Brief description of what to study",
      "date": "YYYY-MM-DD",
      "type": "study"
    }}
  ]
}}

Each task object MUST have: title, description, date (YYYY-MM-DD), type.
Type must be one of: "study", "quiz", "revision".
"""

        human_prompt = """
Syllabus:

{text}

Start date: {start_date}

End date: {end_date}
"""

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_prompt)]
        )

        last_result: str = ""
        for attempt in range(2):
            messages = prompt.format_messages(
                text=json.dumps(syllabus_data, ensure_ascii=False, indent=2),
                start_date=start_date,
                end_date=end_date,
            )
            result = await self._ainvoke_text(messages, temperature=0.3, json_mode=True)
            last_result = result or ""

            try:
                cleaned = self._extract_json(last_result)
                data = json.loads(cleaned)
                if isinstance(data, dict) and data.get("tasks"):
                    return data
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

            logger.warning(
                "Study plan attempt %d returned no valid tasks. "
                "Raw output (first 500 chars): %s",
                attempt + 1,
                last_result[:500] if isinstance(last_result, str) else str(last_result)[:500],
            )

        return {"tasks": [], "summary": last_result}

    # ================================================================
    # REVISION SCHEDULE
    # ================================================================

    async def generate_revision_schedule(
        self,
        syllabus_data: dict,
        start_date: str,
        end_date: Optional[str] = None,
        llm_text: Optional[str] = None,
    ) -> dict:
        system_prompt = """
You are an expert educational revision planner.

Create a spaced repetition revision schedule based ONLY on the supplied syllabus.

Do not invent topics. Use the actual topics/chapters from the syllabus content provided.

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

        human_prompt = """
Syllabus:

{text}

Start date: {start_date}

End date: {end_date}
"""

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_prompt)]
        )

        model = self._get_model(temperature=0.3, json_mode=False)
        chain = prompt | model | self.parser

        text_to_send = llm_text or json.dumps(syllabus_data, ensure_ascii=False, indent=2)
        result = await chain.ainvoke({
            "text": text_to_send,
            "start_date": start_date,
            "end_date": end_date,
        })

        try:
            cleaned = self._extract_json(result)
            data = json.loads(cleaned)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("LLM returned invalid JSON for revision schedule.")

        return {"items": []}

    # ================================================================
    # WEAK TOPIC ANALYSIS
    # ================================================================

    async def analyze_weak_topics(
        self,
        quiz_results: List[dict],
        syllabus_data: dict,
    ) -> List[dict]:
        system_prompt = """
You are an educational analytics expert.

Analyze the quiz results and identify weak topics.

Use ONLY the supplied quiz results and syllabus.

For each weak topic return:
- topic_name
- accuracy
- confidence_level
- total_attempts
- recommended_action

Return ONLY a valid JSON array.
"""

        human_prompt = """
Quiz results:

{quiz_results}

Syllabus:

{text}
"""

        prompt = ChatPromptTemplate.from_messages(
            [("system", system_prompt), ("human", human_prompt)]
        )

        model = self._get_model(temperature=0.3, json_mode=False)
        chain = prompt | model | self.parser
        result = await chain.ainvoke({
            "quiz_results": json.dumps(quiz_results, ensure_ascii=False, indent=2),
            "text": json.dumps(syllabus_data, ensure_ascii=False, indent=2),
        })

        try:
            cleaned = self._extract_json(result)
            data = json.loads(cleaned)
            if isinstance(data, list):
                return data
        except (json.JSONDecodeError, TypeError, ValueError):
            logger.warning("LLM returned invalid JSON for weak-topic analysis.")

        return []
