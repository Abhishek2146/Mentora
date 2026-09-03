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


def build_course_overview_document(
    syllabus_id: int,
    user_id: int,
    subjects: List[Dict[str, Any]],
    course_name: Optional[str] = None,
    source_name: str = "syllabus",
    credit_hours: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """Build a single course-level overview document for the RAG index.

    This document aggregates every unit name, topic list, and credit/hour
    information into one chunk so that broad queries like:
      - "what are the main topics covered?"
      - "how many credit hours does this course have?"
      - "list all units"
    can be answered from a single retrieved document without needing to
    assemble many per-unit chunks.

    Returns a {"content": str, "metadata": dict} dict, or None when there
    are no usable subjects/chapters.
    """
    all_chapters: List[Dict[str, Any]] = []
    for subj in subjects:
        if not isinstance(subj, dict):
            continue
        all_chapters.extend(subj.get("chapters") or [])

    if not all_chapters:
        return None

    first_subj = subjects[0] if subjects else {}
    display_course = course_name or (first_subj.get("name") or "").strip() or "Course"

    total_hours = sum(
        coerce_hour_value(ch.get("estimated_hours")) for ch in all_chapters
    )
    # Use extracted credit_hours if available, otherwise fall back to total_hours
    # from parsed unit durations.
    effective_credits = credit_hours if credit_hours is not None else (
        total_hours if total_hours > 0 else None
    )

    lines: List[str] = [
        f"Course: {display_course}",
        f"Total Units: {len(all_chapters)}",
    ]
    if effective_credits is not None:
        lines.append(f"Credit Hours: {effective_credits}")
    if total_hours > 0:
        lines.append(f"Total Teaching Hours: {total_hours}")

    lines.append("")
    lines.append("Course Overview - All Units and Topics:")
    lines.append("")

    unit_number = 0
    for chap in all_chapters:
        if not isinstance(chap, dict):
            continue
        chap_name = str(chap.get("name") or "").strip()
        if not chap_name:
            continue
        unit_number += 1
        hours = coerce_hour_value(chap.get("estimated_hours"))
        topics: List[str] = [
            str(t).strip()
            for t in (chap.get("topics") or [])
            if str(t).strip()
        ]

        heading = format_unit_heading(unit_number, chap_name)
        if hours:
            heading += f" ({hours} hrs)"
        lines.append(heading)
        for t in topics:
            lines.append(f"  - {t}")
        lines.append("")

    content = "\n".join(lines).strip()
    if not content:
        return None

    metadata = {
        "user_id": user_id,
        "syllabus_id": syllabus_id,
        "source": source_name,
        "doc_type": "course_overview",
        "unit_number": 0,
        "unit_title": "Course Overview",
    }
    logger.info(
        "[VECTOR] Built course overview document for syllabus_id=%s "
        "(%d units, credit_hours=%s, total_hours=%d)",
        syllabus_id, len(all_chapters), effective_credits, total_hours,
    )
    return {"content": content, "metadata": metadata}


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
        "You are Mentora, an AI tutor integrated with a syllabus-based RAG system.",
        "The backend automatically retrieves and provides relevant syllabus content "
        "and documents as context before the student's question.",
        "You MUST use the provided retrieved context when answering the student's question.",
        "IMPORTANT: The student should NOT be asked to provide the syllabus, syllabus "
        "context, or retrieved documents again. The backend already provides them.",
        "Do not say: 'Please provide the syllabus', 'Please provide syllabus context', "
        "'Please provide retrieved documents', 'I need the syllabus to answer', "
        "'I am ready to help. Please provide...', 'Select a syllabus to get started'.",
        "The student has already selected the syllabus in the Mentora application.",
        "Simply process the student's question.",
    ]

    if context:
        grounding_rules = (
            "The retrieved syllabus/document context is provided below. "
            "Treat the retrieved context as the primary source for syllabus-related questions.\n"
            "CONTEXT USAGE RULES:\n"
            "1. If the answer is available in the retrieved context, answer directly.\n"
            "2. If the retrieved context contains only topic names but not detailed "
            "explanations, explain only what can reasonably be derived from the "
            "available context and general academic knowledge.\n"
            "3. If the requested information is genuinely unavailable, say: "
            "'The provided syllabus does not contain enough information to answer "
            "this question in detail.'\n"
            "4. Do not ask the student to upload or provide the syllabus again.\n"
            "5. Use ONLY unit names, topic names, and hours that appear verbatim "
            "in the context. Never invent or add topics, units, hours, or course codes.\n"
            "6. Never say the subject or course is 'Unknown' when the context identifies it.\n"
            "7. Never claim information is missing if it is present in the context.\n"
            "8. Never answer syllabus questions with generic suggestions such as "
            "'some topics could include' or 'topics might include'.\n"
            "9. When explaining a concept that IS part of the syllabus you may draw "
            "on general teaching knowledge, but always keep the syllabus unit/topic "
            "structure as the frame of reference."
        )
        parts.append(grounding_rules)
        if syllabus_title:
            parts.append(f"The student's current syllabus/course is titled: {syllabus_title}.")
        parts.append("RETRIEVED SYLLABUS CONTEXT:\n" + context)
    elif syllabus_selected:
        parts.append(
            "The student selected a syllabus, but no relevant content could "
            "be retrieved from it for this question. Tell them clearly that "
            "you couldn't find this topic in the uploaded syllabus. Do not "
            "guess the course structure and do not invent topics."
        )

    if personalization:
        parts.append(personalization)

    response_format_rules = (
        "CORE RESPONSE RULE:\n"
        "Prefer structured points over paragraphs. Use short points instead of long "
        "explanations. Every major concept should be separated into its own numbered "
        "section. Do not combine multiple concepts into one long paragraph. Do not "
        "generate unnecessary introductory or concluding paragraphs. Think of every "
        "response as STUDY NOTES, not an essay.\n\n"
        "CRITICAL NEWLINE RULE:\n"
        "Every numbered point MUST be on its own separate line. Each point must start "
        "on a new line. Never put multiple points on the same line. Never combine "
        "points into a single line or paragraph. There must be a line break between "
        "every numbered item.\n"
        "Correct format:\n"
        "1. First point here.\n"
        "2. Second point here.\n"
        "3. Third point here.\n"
        "Wrong format:\n"
        "1. First point here. 2. Second point here. 3. Third point here.\n"
        "Wrong format:\n"
        "1. First point here. 2. Second point here. 3. Third point here\n\n"
        "FORMATTING RULES:\n"
        "Do NOT use: asterisks such as **, asterisk bullets *, hyphen bullets -, "
        "Markdown tables, large paragraph blocks, excessive Markdown formatting.\n"
        "Do use: numbered points each on its own line, simple headings, short "
        "sub-points written as separate lines, labels such as Definition, Key "
        "Points, Example, Importance, Advantages, Limitations.\n"
        "Every numbered item must start on a new line with a line break before it.\n\n"
        "ANSWER STRUCTURE - Choose based on the question:\n\n"
        "CASE 1: 'What are...' / 'List...' / 'Types of...'\n"
        "Topic Name\n"
        "1. Topic One\n"
        "   Short explanation.\n"
        "2. Topic Two\n"
        "   Short explanation.\n"
        "3. Topic Three\n"
        "   Short explanation.\n\n"
        "CASE 2: 'What is...' / 'Define...'\n"
        "Topic Name\n"
        "Definition:\n"
        "One or two concise sentences.\n"
        "Key Points:\n"
        "1. Important point.\n"
        "2. Important point.\n"
        "3. Important point.\n"
        "Example:\n"
        "One simple example.\n\n"
        "CASE 3: 'Explain...' / 'Describe...'\n"
        "Topic Name\n"
        "Definition:\n"
        "Short definition.\n"
        "Explanation:\n"
        "1. First important concept.\n"
        "2. Second important concept.\n"
        "3. Third important concept.\n"
        "Example:\n"
        "Simple example.\n"
        "Key Point:\n"
        "One short takeaway.\n\n"
        "CASE 4: 'Explain in detail'\n"
        "Topic Name\n"
        "1. Definition\n"
        "   Concise definition.\n"
        "2. Main Concept\n"
        "   Concise explanation.\n"
        "3. Working\n"
        "   Step-by-step explanation.\n"
        "4. Key Features\n"
        "   1. Feature one.\n"
        "   2. Feature two.\n"
        "5. Example\n"
        "   Simple example.\n"
        "6. Advantages\n"
        "   1. Advantage one.\n"
        "   2. Advantage two.\n"
        "7. Limitations\n"
        "   1. Limitation one.\n"
        "   2. Limitation two.\n"
        "8. Applications\n"
        "   1. Application one.\n"
        "   2. Application two.\n"
        "Only include sections that are relevant to the topic.\n\n"
        "CASE 5: Comparison\n"
        "Never use a table.\n"
        "Topic A\n"
        "Definition:\n"
        "...\n"
        "Key Points:\n"
        "1. ...\n"
        "2. ...\n"
        "Topic B\n"
        "Definition:\n"
        "...\n"
        "Key Points:\n"
        "1. ...\n"
        "2. ...\n"
        "Differences:\n"
        "1. ...\n"
        "2. ...\n"
        "3. ...\n\n"
        "CASE 6: Main Topics of a Unit\n"
        "Unit Name\n"
        "1. Topic Name\n"
        "   Short description.\n"
        "2. Topic Name\n"
        "   Short description.\n\n"
        "CASE 7: Exam-Oriented Answer\n"
        "Topic Name\n"
        "Definition:\n"
        "...\n"
        "Important Points:\n"
        "1. ...\n"
        "2. ...\n"
        "3. ...\n"
        "Example:\n"
        "...\n"
        "Exam Tip:\n"
        "...\n\n"
        "CASE 8: User asks for simple explanation\n"
        "Topic Name\n"
        "Simple Explanation:\n"
        "1. ...\n"
        "2. ...\n"
        "3. ...\n"
        "Example:\n"
        "...\n\n"
        "CONTENT RULES:\n"
        "1. Stay relevant to the student's question.\n"
        "2. Use syllabus terminology where appropriate.\n"
        "3. Do not invent syllabus topics.\n"
        "4. Do not unnecessarily repeat information.\n"
        "5. Keep each point concise, 1 to 3 sentences per point.\n"
        "6. Break long explanations into multiple numbered points.\n"
        "7. Use examples when they improve understanding.\n"
        "8. Do not write one large paragraph containing multiple concepts.\n"
        "9. If the question asks for a list, provide a list.\n"
        "10. If the question asks for an explanation, provide structured explanation points.\n"
        "11. If the question asks for a definition, start with a concise definition.\n"
        "12. If the question asks for differences, provide numbered differences.\n\n"
        "STYLE RULE:\n"
        "Think of every response as STUDY NOTES, not an essay.\n"
        "Bad example: 'Advanced database models are specialized data models that extend "
        "beyond the traditional relational model to address specific types of data and "
        "application requirements. They provide structures...'\n"
        "Good example:\n"
        "Advanced Database Models\n"
        "Definition:\n"
        "Advanced database models extend traditional models to support specialized data.\n"
        "1. Active Database\n"
        "   Automatically reacts to database events.\n"
        "   Uses triggers to perform predefined actions.\n"
        "2. Temporal Database\n"
        "   Manages time-related data.\n"
        "   Maintains historical information.\n"
        "3. Spatial Database\n"
        "   Manages geographic and geometric data.\n"
        "   Commonly used in mapping applications.\n\n"
        "FINAL QUALITY CHECK before returning:\n"
        "1. Is the answer structured?\n"
        "2. Are the main concepts separated?\n"
        "3. Are points short and clear?\n"
        "4. Did I avoid large paragraphs?\n"
        "5. Did I avoid ** formatting?\n"
        "6. Did I avoid * bullets?\n"
        "7. Did I avoid - bullets?\n"
        "8. Did I avoid Markdown tables?\n"
        "9. Did I use numbered points where appropriate?\n"
        "10. Is every numbered point on its own separate line with a line break?\n"
        "11. Did I directly answer the student's question?\n"
        "12. Did I use the selected syllabus/retrieved context?\n"
        "13. Did I avoid asking the student to provide the syllabus or context?\n"
        "If an answer contains a long paragraph that can be divided into points, "
        "divide it into points before returning it.\n"
        "Each numbered point MUST start on a new line. Never put two points on "
        "the same line.\n"
        "Return ONLY the final answer to the student's question."
    )
    parts.append(response_format_rules)

    return "\n\n".join(parts)
