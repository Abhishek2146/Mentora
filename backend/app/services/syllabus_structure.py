"""
Syllabus structure helpers.

Pure (stdlib-only) functions shared by the syllabus parsing, database
storage, vector-indexing, and tutor-retrieval stages.  Keeping this logic
in a dependency-free module means it can be unit-tested without loading
Chroma / HuggingFace imports.

The canonical parsed-syllabus shape used across the project is:

    {
        "subjects": [
            {
                "name": str,            # course / subject title
                "description": str,
                "chapters": [           # chapters == document units
                    {
                        "name": str,            # verbatim unit heading
                        "description": str,
                        "topics": [str],        # verbatim topic names
                        "estimated_hours": int, # 0 when source states none
                    }
                ],
            }
        ]
    }
"""

import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.core.logger import get_logger

logger = get_logger(__name__)


# ============================================================
# Pseudo-unit detection
# ============================================================

# Document section headings that must NOT become units/chapters on their
# own.  Matching is exact-phrase (anchored), so "Introduction to Computer"
# is NOT rejected while the bare section heading "Introduction" is.
_PSEUDO_UNIT_PHRASES = (
    "syllabus",
    "course syllabus",
    "course contents",
    "course content",
    "contents",
    "table of contents",
    "course description",
    "description",
    "objectives",
    "objective",
    "course objectives",
    "learning objectives",
    "learning objective",
    "learning outcomes",
    "learning outcome",
    "course outcomes",
    "aims and objectives",
    "references",
    "reference",
    "reference books",
    "bibliography",
    "textbooks",
    "text book",
    "text books",
    "prescribed textbooks",
    "evaluation",
    "evaluation scheme",
    "assessment",
    "assessment scheme",
    "grading",
    "grading scheme",
    "marks distribution",
    "marking scheme",
    "teaching scheme",
    "prerequisites",
    "prerequisite",
    "introduction",
)

# A heading that is explicitly numbered as a unit/module/chapter in the
# source document (e.g. "Unit 5: Syllabus", "Module 3 - Evaluation") is a
# REAL unit regardless of its title text.
_EXPLICIT_UNIT_RE = re.compile(
    r"^\s*(?:unit|module|chapter|part|week|lecture|section)\s*\.?\s*\w+"
    r"|^\s*u\s*\.?\s*\d+",
    re.IGNORECASE,
)

_PSEUDO_CACHE: Dict[str, bool] = {}

# Matches trailing hours annotations like "(4 Hrs.)", "(3 Hours)" at the
# end of a chapter name.  Used to extract hours when the LLM embeds them
# in the name instead of setting estimated_hours.
_HOURS_IN_NAME_RE = re.compile(
    r"\s*\((\d+(?:\.\d+)?)\s*(?:Hrs?\.?|Hours?\.?)\)\s*$",
    re.IGNORECASE,
)


def is_pseudo_unit_heading(name: Any) -> bool:
    """True when ``name`` is one of the generic section headings that must
    not be treated as a course unit (unless explicitly numbered)."""
    if not isinstance(name, str):
        return False
    key = name.strip().casefold()
    if not key:
        return False
    if key in _PSEUDO_CACHE:
        return _PSEUDO_CACHE[key]

    if _EXPLICIT_UNIT_RE.match(key):
        result = False
    else:
        # Strip trailing punctuation/numbering decorations ("1.", "(4 Hrs.)")
        stripped = re.sub(
            r"[\s:.\-\(\)]*(\d+\s*(?:hrs?|hours?))?[\s:.\-\(\)]*$", "", key
        ).strip()
        stripped = re.sub(r"^\d+[\s:.:\-]+", "", stripped).strip()
        result = stripped in _PSEUDO_UNIT_PHRASES

    _PSEUDO_CACHE[key] = result
    return result


# ============================================================
# Hours coercion
# ============================================================

def coerce_hour_value(value: Any) -> int:
    """Best-effort conversion of an LLM/source hours value to int.

    Accepts ints/floats/numeric strings/phrases like "3 Hrs.".
    Anything unusable becomes 0 - hours are never invented.
    """
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        coerced = value
    elif isinstance(value, float):
        coerced = int(value)
    elif isinstance(value, str):
        match = re.search(r"\d+", value)
        if not match:
            return 0
        coerced = int(match.group())
    else:
        return 0
    return max(0, coerced)


# ============================================================
# Unit-number extraction
# ============================================================

# "Unit 4: ...", "unit 10.", "U3 ...", "Module 2 - ..." -> 4 / 10 / 3 / 2
_UNIT_NUMBER_RE = re.compile(
    r"^\s*(?:unit|module|chapter|part|week|lecture|section|u)\s*\.?\s*(\d+)",
    re.IGNORECASE,
)


def extract_unit_number(name: Any) -> Optional[int]:
    """Return the explicit unit number a heading starts with, else None.

    Only *leading* numbers count: "Unit 4: Input Devices" -> 4 while
    "Input Devices for Unit 4" -> None.  Used to keep units in source
    document order no matter what order the LLM emitted them in.
    """
    if not isinstance(name, str):
        return None
    match = _UNIT_NUMBER_RE.match(name.strip())
    return int(match.group(1)) if match else None


def sort_chapters_by_source_order(chapters: List[Dict[str, Any]]) -> None:
    """Stable-sort chapters in place by their leading unit number.

    Chapters without an explicit number keep their relative position at
    the end of the run (stable sort), so unnumbered sections such as
    "Laboratory Works" never displace numbered units.
    """
    def key(indexed):
        position, chapter = indexed
        number = extract_unit_number(chapter.get("name"))
        # Numbered first (ascending), then unnumbered in original order.
        if number is None:
            number = 10**9 + position
        return number

    chapters[:] = [c for _, c in sorted(list(enumerate(chapters)), key=key)]


# ============================================================
# Regex-based syllabus extraction (LLM-free)
# ============================================================

# Matches "Unit 1:", "Unit 1.", "Unit 1 -", "Module 3:", etc.
_UNIT_HEADING_RE = re.compile(
    r"^\s*(?:Unit|Module|Chapter|Part|Week)\s+(\d+)\s*[:.\-\)]*\s*(.*)",
    re.IGNORECASE | re.MULTILINE,
)

# Matches trailing hours like "(3 Hrs.)", "(4 Hours)", "(5 Hr.)"
_HOURS_RE = re.compile(
    r"\((\d+(?:\.\d+)?)\s*(?:Hrs?\.?|Hours?\.?)\)",
    re.IGNORECASE,
)

# Pseudo-unit section headings that should never become chapters.
_PSEUDO_SECTION_NAMES = frozenset({
    "introduction", "syllabus", "course syllabus", "course contents",
    "course content", "contents", "table of contents", "course description",
    "description", "objectives", "objective", "course objectives",
    "learning objectives", "learning objective", "learning outcomes",
    "learning outcome", "course outcomes", "aims and objectives",
    "references", "reference", "reference books", "bibliography",
    "textbooks", "text book", "text books", "prescribed textbooks",
    "evaluation", "evaluation scheme", "assessment", "assessment scheme",
    "grading", "grading scheme", "marks distribution", "marking scheme",
    "teaching scheme", "prerequisites", "prerequisite",
    "laboratory works", "laboratory", "lab",
})


def try_regex_parse(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to extract syllabus structure via regex.

    Works for syllabi with explicit "Unit N:" headings followed by
    topic lists.  Returns None when the text does not match this
    pattern (caller should fall back to LLM parsing).
    """
    if not text or not text.strip():
        return None

    # Find all unit headings with their numbers
    headings: List[Tuple[int, str, int]] = []  # (unit_num, title, position)
    for match in _UNIT_HEADING_RE.finditer(text):
        unit_num = int(match.group(1))
        title = match.group(2).strip()
        headings.append((unit_num, title, match.start()))

    if len(headings) < 2:
        return None

    # Extract course title from the first meaningful line
    course_title = ""
    for line in text.splitlines():
        line = line.strip()
        if line and len(line) > 5 and not line.startswith(("Full Marks", "Pass Marks", "Course No", "Nature", "Semester", "Course Description", "Course Objectives", "Course Contents")):
            course_title = line
            break

    chapters: List[Dict[str, Any]] = []
    for i, (unit_num, title, start) in enumerate(headings):
        # End of this unit's content is the start of the next heading (or end of text)
        end = headings[i + 1][2] if i + 1 < len(headings) else len(text)
        body = text[start:end]

        # Extract hours from the heading line
        hours = 0
        hours_match = _HOURS_RE.search(title)
        if hours_match:
            hours = coerce_hour_value(hours_match.group(1))
            title = title[:hours_match.start()].strip()

        # Skip pseudo-sections (e.g. "Unit 13: Laboratory Works")
        clean_title = re.sub(r"^\d+\s*[:.\-\)]*\s*", "", title).strip()
        if clean_title.casefold() in _PSEUDO_SECTION_NAMES:
            logger.info(
                "[REGEX] Skipping pseudo-unit %r (unit %d)",
                clean_title or title, unit_num,
            )
            continue

        # If title is empty, use a generic name
        if not title:
            title = f"Unit {unit_num}"

        # Extract topics from the body: everything after the heading line
        # until the next heading.  Topics are typically separated by
        # semicolons, newlines, or bullet points.
        lines = body.splitlines()
        topic_text = ""
        heading_seen = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip lines that look like unit headings (including this
            # unit's own heading which may appear after a blank line).
            if _UNIT_HEADING_RE.match(line):
                heading_seen = True
                continue
            if not heading_seen:
                continue
            topic_text += " " + line

        # Split on semicolons first (common in syllabi), then newlines
        raw_topics = re.split(r"[;]\s*", topic_text)
        topics = []
        for t in raw_topics:
            t = t.strip()
            if not t or len(t) < 2:
                continue
            # Skip lines that are just "Introduction" or similar
            if t.casefold() in _PSEUDO_SECTION_NAMES:
                continue
            topics.append(t)

        chapters.append({
            "name": f"Unit {unit_num}: {title}",
            "description": "",
            "topics": topics,
            "estimated_hours": hours,
        })

    if not chapters:
        return None

    logger.info(
        "[REGEX] Extracted %d units from OCR text (course: %r)",
        len(chapters), course_title,
    )
    for ch in chapters:
        logger.info(
            "[REGEX] Unit: %r | hours=%s | topics=%d",
            ch["name"],
            ch["estimated_hours"] if ch["estimated_hours"] else "not stated",
            len(ch["topics"]),
        )

    return {
        "subjects": [{
            "name": course_title or "Course",
            "description": "",
            "chapters": chapters,
        }]
    }


# ============================================================
# Parsed-syllabus cleaning / validation (pre-database)
# ============================================================

def consolidate_fragmented_subjects(
    subjects: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], bool]:
    """Merge subject fragments that actually belong to one course.

    Small models frequently split a single-course syllabus into several
    subjects (invented names like "Data Representation", or promoted
    unit headings).  Signal that fragments belong together: every
    explicit unit number appears at most once across ALL subjects - i.e.
    numbering never restarts.  Genuine multi-course documents renumber
    from 1 per course, which triggers duplicates and blocks the merge.

    Returns (subjects, merged_flag).
    """
    if len(subjects) <= 1:
        return subjects, False

    seen_numbers: Dict[int, int] = {}
    for index, subj in enumerate(subjects):
        for chap in subj.get("chapters", []):
            number = extract_unit_number(chap.get("name"))
            if number is not None:
                if number in seen_numbers:
                    logger.info(
                        "[PARSER] unit number %d repeats across subjects; "
                        "treating them as separate courses", number,
                    )
                    return subjects, False
                seen_numbers[number] = index

    if not seen_numbers:
        return subjects, False

    # Prefer a subject that actually holds chapters as the survivor.
    order = sorted(
        range(len(subjects)),
        key=lambda i: (0 if subjects[i]["chapters"] else 1, i),
    )
    base_index = order[0]
    base = subjects[base_index]
    for index in order[1:]:
        frag = subjects[index]
        if frag is base:
            continue
        base["chapters"].extend(frag["chapters"])
        logger.warning(
            "[PARSER] consolidated fragmented subject %r into course "
            "subject %r (+%d chapters)",
            frag["name"], base["name"], len(frag["chapters"]),
        )

    # De-duplicate chapters by casefolded name, keeping first occurrence.
    unique: Dict[str, Dict[str, Any]] = {}
    for chap in base["chapters"]:
        key = str(chap.get("name") or "").strip().casefold()
        if key and key not in unique:
            unique[key] = chap
    base["chapters"] = list(unique.values())

    sort_chapters_by_source_order(base["chapters"])
    return [base], True


def clean_parsed_syllabus(parsed_data: Any) -> Dict[str, Any]:
    """Validate and clean LLM-parsed syllabus data before it reaches the DB.

    Rules:
    - Chapters whose name is a generic section heading ("Syllabus",
      "Objectives", ...) are rejected unless explicitly unit-numbered.
    - Duplicate chapters (case-insensitive) are removed; first wins and
      original ordering is preserved.
    - Hours are coerced to non-negative ints; missing stays 0 (never
      invented or redistributed).
    - Topics are stripped of whitespace, de-duplicated case-insensitively,
      and kept verbatim otherwise.
    - Nameless chapters with no topics are dropped.

    Returns the cleaned dict with at least {"subjects": [...]}.  Raises
    ValueError when nothing usable remains.
    """
    if not isinstance(parsed_data, dict):
        raise ValueError("Parsed syllabus must be a JSON object")

    subjects = parsed_data.get("subjects")
    if subjects is None:
        subjects = []

    cleaned_subjects: List[Dict[str, Any]] = []
    total_units = 0

    for subj_index, subj in enumerate(subjects):
        if not isinstance(subj, dict):
            continue
        subj_name = str(subj.get("name") or "").strip() or f"Subject {subj_index + 1}"
        chapters_in = subj.get("chapters") or []
        if not isinstance(chapters_in, list):
            chapters_in = []

        seen_chapter_keys = set()
        cleaned_chapters: List[Dict[str, Any]] = []

        for chap in chapters_in:
            if not isinstance(chap, dict):
                continue
            chap_name = str(chap.get("name") or "").strip()
            topics_raw = chap.get("topics")
            topics = _clean_topics(topics_raw)
            hours = coerce_hour_value(chap.get("estimated_hours"))

            if not chap_name and not topics:
                logger.warning("[DB] dropping chapter without name/topics in subject %r", subj_name)
                continue

            if not chap_name and topics:
                logger.warning("[DB] dropping unnamed chapter with %d topics in subject %r", len(topics), subj_name)
                continue

            if is_pseudo_unit_heading(chap_name):
                logger.warning(
                    "[DB] rejected pseudo-unit chapter %r in subject %r "
                    "(generic section heading, not defined as a unit in the source)",
                    chap_name, subj_name,
                )
                continue

            chap_key = chap_name.casefold()
            if chap_key in seen_chapter_keys:
                logger.warning("[DB] dropping duplicate chapter %r in subject %r", chap_name, subj_name)
                continue
            seen_chapter_keys.add(chap_key)

            # If the LLM embedded hours in the name (e.g. "(4 Hrs.)")
            # but left estimated_hours at 0, extract them and strip the
            # annotation from the display name.
            if hours == 0:
                hm = _HOURS_IN_NAME_RE.search(chap_name)
                if hm:
                    hours = coerce_hour_value(hm.group(1))
                    chap_name = chap_name[: hm.start()].rstrip()
                    logger.info(
                        "[DB] Extracted %d hrs from chapter name %r",
                        hours, chap_name,
                    )

            cleaned_chapters.append({
                "name": chap_name,
                "description": str(chap.get("description") or ""),
                "topics": topics,
                "estimated_hours": hours,
            })
            logger.info(
                "[DB] Unit: %r | hours=%s | topics=%d",
                chap_name, hours if hours else "not stated",
                len(topics),
            )
            for topic in topics:
                logger.info("[DB] Topic: %r (unit=%r)", topic, chap_name)

        if cleaned_chapters:
            cleaned_subjects.append({
                "name": subj_name,
                "description": str(subj.get("description") or ""),
                "chapters": cleaned_chapters,
            })
            total_units += len(cleaned_chapters)

    # Fold subject fragments of a single course back together and put
    # every unit in source-document order (by its explicit number).
    if cleaned_subjects:
        cleaned_subjects, merged = consolidate_fragmented_subjects(
            cleaned_subjects
        )
        if merged:
            total_units = sum(
                len(s["chapters"]) for s in cleaned_subjects
            )
        for subj in cleaned_subjects:
            sort_chapters_by_source_order(subj["chapters"])

    logger.info("[PARSER] Course: %r", cleaned_subjects[0]["name"] if cleaned_subjects else None)
    logger.info(
        "[PARSER] Parsed %d subject(s), %d valid unit(s) after validation",
        len(cleaned_subjects), total_units,
    )

    if not cleaned_subjects:
        raise ValueError(
            "Parsed syllabus contained no valid units after validation"
        )

    return {"subjects": cleaned_subjects}


def _clean_topics(topics_raw: Any) -> List[str]:
    """Normalize a chapter's topics to a clean list of verbatim strings."""
    if topics_raw is None:
        return []
    if isinstance(topics_raw, str):
        topics_raw = [topics_raw]
    if not isinstance(topics_raw, list):
        return []

    cleaned: List[str] = []
    seen = set()
    for topic in topics_raw:
        if isinstance(topic, dict):
            topic = (
                topic.get("name")
                or topic.get("title")
                or topic.get("topic")
                or topic.get("topic_name")
            )
        if topic is None:
            continue
        topic_str = str(topic).strip()
        if not topic_str:
            continue
        key = topic_str.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(topic_str)
    return cleaned


# ============================================================
# Structured RAG documents
# ============================================================

# Headings that already carry their own numbering in the source document
# ("Unit 2: ...", "U3 ...", "Module 4 - ...").  Such titles are shown
# verbatim instead of receiving a second, possibly conflicting index.
_UNIT_PREFIX_RE = re.compile(
    r"^\s*(?:unit|module|chapter|part|week|lecture|section)\b"
    r"|^\s*u\s*\d+",
    re.IGNORECASE,
)


def format_unit_heading(unit_number: Any, title: Any) -> str:
    """Return one clean ``Unit ...`` heading line.

    Verbatim source headings keep their own numbering when they already
    start with a unit marker; otherwise the global running number is
    prepended (or a bare ``Unit:`` label when no number exists).
    """
    text = str(title or "").strip()
    if not text:
        return f"Unit {unit_number}" if unit_number else "Unit"
    if _UNIT_PREFIX_RE.match(text):
        return text
    if unit_number:
        return f"Unit {unit_number}: {text}"
    return f"Unit: {text}"


def build_unit_rag_documents(
    syllabus_id: int,
    user_id: int,
    subjects: List[Dict[str, Any]],
    course_name: Optional[str] = None,
    source_name: str = "syllabus",
) -> List[Dict[str, Any]]:
    """Build structured vector documents from validated parsed syllabus data.

    Produces one document per unit (heading + all topics) and one document
    per individual topic, each carrying metadata that traces back to the
    uploaded syllabus:

        {
            "user_id": ..., "syllabus_id": ...,
            "unit_number": N, "unit_title": "...",
            "topic_title": "..." | omitted for unit docs,
            "source": "syllabus",
        }

    Returns a list of {"content": str, "metadata": dict} dicts (conversion
    to langchain Documents happens in the embedding service layer).
    """
    documents: List[Dict[str, Any]] = []

    def _add(content: str, metadata: Dict[str, Any]) -> None:
        if content.strip():
            documents.append({"content": content.strip(), "metadata": metadata})

    unit_number = 0
    for subj in subjects:
        if not isinstance(subj, dict):
            continue
        subj_name = str(subj.get("name") or "").strip()
        display_course = course_name or subj_name or "Course"

        for chap in subj.get("chapters", []) or []:
            if not isinstance(chap, dict):
                continue
            chap_name = str(chap.get("name") or "").strip()
            if not chap_name:
                continue
            unit_number += 1
            topics: List[str] = [
                str(t).strip()
                for t in (chap.get("topics") or [])
                if str(t).strip()
            ]
            hours = coerce_hour_value(chap.get("estimated_hours"))

            lines = [
                f"Course: {display_course}",
                format_unit_heading(unit_number, chap_name),
            ]
            if hours:
                lines.append(f"Hours: {hours}")
            if topics:
                lines.append("Topics:")
                lines.extend(f"- {t}" for t in topics)
            base_meta = {
                "user_id": user_id,
                "syllabus_id": syllabus_id,
                "unit_number": unit_number,
                "unit_title": chap_name,
                "source": source_name,
            }
            _add("\n".join(lines), dict(base_meta))

            for topic in topics:
                _add(
                    "\n".join([
                        f"Course: {display_course}",
                        format_unit_heading(unit_number, chap_name),
                        f"Topic: {topic}",
                    ]),
                    {
                        **base_meta,
                        "topic_title": topic,
                    },
                )
            logger.info(
                "[VECTOR] syllabus_id=%s unit_number=%d unit=%r topics=%d",
                syllabus_id, unit_number, chap_name, len(topics),
            )

    return documents


# ============================================================
# Retrieval context formatting
# ============================================================

def format_retrieval_context(documents: Iterable[Any]) -> str:
    """Format retrieved chunks into labeled SOURCE blocks.

    Each block carries Course / Unit / Topic headers derived from chunk
    metadata so the LLM can ground its answer precisely.  Falls back to
    legacy metadata keys (subject/chapter/topic) when present.
    """
    blocks: List[str] = []
    for i, doc in enumerate(documents, start=1):
        meta = getattr(doc, "metadata", None) or {}
        course = (
            meta.get("course_name")
            or meta.get("subject")
            or ""
        )
        unit_title = meta.get("unit_title") or meta.get("chapter") or ""
        unit_number = meta.get("unit_number")
        topic = meta.get("topic_title") or meta.get("topic") or ""

        header_lines = []
        if course:
            header_lines.append(f"Course: {course}")
        if unit_title:
            header_lines.append(format_unit_heading(unit_number, unit_title))
        if topic:
            header_lines.append(f"Topic: {topic}")

        content = getattr(doc, "page_content", "") or str(doc)
        block = (
            f"SOURCE {i}\n"
            + ("\n".join(header_lines) + "\n" if header_lines else "")
            + f"Content:\n{content.strip()}"
        )
        blocks.append(block)
        logger.info(
            "[RETRIEVED METADATA]: syllabus_id=%s unit=%r topic=%r source=%s",
            meta.get("syllabus_id"),
            unit_title or None,
            topic or None,
            meta.get("source"),
        )
    return "\n\n".join(blocks)


# ============================================================
# Tutor grounding helpers
# ============================================================

TUTOR_NOT_FOUND_MESSAGE = (
    "I couldn't find that information in the uploaded syllabus. "
    "Please check your syllabus, or ask me about a specific unit or "
    "topic that appears in it."
)


def build_tutor_system_prompt(
    context: str,
    syllabus_selected: bool,
    personalization: str = "",
    syllabus_title: str = "",
) -> str:
    """Build a strictly syllabus-grounded system prompt for the AI Tutor."""
    parts: List[str] = [
        "You are an AI tutor for the student's uploaded syllabus."
    ]

    if context:
        grounding_rules = (
            "Use the SYLLABUS CONTEXT below as the primary and authoritative "
            "source for any question about the course, its units, topics, or "
            "hours. Strict rules:\n"
            "- Use ONLY unit names, topic names, and hours that appear "
            "verbatim in the context. Never invent or add topics, units, "
            "hours, or course codes.\n"
            "- Never say the subject or course is 'Unknown' when the context "
            "identifies it.\n"
            "- Never claim information is missing if it is present in the "
            "context.\n"
            "- Never answer syllabus questions with generic suggestions such "
            "as 'some topics could include' or 'topics might include'.\n"
            "- If the specific information asked about does not appear in "
            "the context, state clearly that it was not found in the "
            "uploaded syllabus before offering anything general.\n"
            "- When explaining a concept that IS part of the syllabus you "
            "may draw on general teaching knowledge, but always keep the "
            "syllabus unit/topic structure as the frame of reference."
        )
        parts.append(grounding_rules)
        if syllabus_title:
            parts.append(f"The student's current syllabus/course is titled: {syllabus_title}.")
        parts.append("SYLLABUS CONTEXT:\n" + context)
    elif syllabus_selected:
        parts.append(
            "The student selected a syllabus, but no relevant content could "
            "be retrieved from it for this question. Tell them clearly that "
            "you couldn't find this topic in the uploaded syllabus. Do not "
            "guess the course structure and do not invent topics."
        )

    if personalization:
        parts.append(personalization)

    return "\n\n".join(parts)
