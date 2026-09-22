from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.auth import get_current_user_id
from app.core.logger import get_logger
from app.core.quotas import QuotaContext, record_usage, require_ai_quota
from app.database.database import get_db
from app.models.note import Note
from app.models.syllabus import Syllabus
from app.models.subscription import UsageType
from app.schemas.note import (
    NoteCreate,
    NoteOut,
    NoteUpdate,
    NoteSummaryOut,
    SyllabusNoteGenerateRequest,
)

router = APIRouter()
logger = get_logger(__name__)


import re

def strip_markdown(text: str) -> str:
    """Strip markdown formatting symbols to return clean plain text."""
    if not text:
        return ""
    # Remove code blocks ``` ... ```
    text = re.sub(r"```[a-zA-Z]*\n?([\s\S]*?)\n?```", r"\1", text)
    # Remove inline code ` ... `
    text = re.sub(r"`([^`]+)`", r"\1", text)
    # Remove headers (# Header, ## Header, etc)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove bold & italic (**text**, *text*, __text__, _text_)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    # Replace markdown bullet points (- or *) with clean bullet character •
    text = re.sub(r"^\s*[-*]\s+", "• ", text, flags=re.MULTILINE)
    # Remove blockquotes (> quote)
    text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)
    return text.strip()


# ------------------------------------------------------------------ helpers

async def _get_owned_note(
    note_id: int,
    user_id: int,
    db: AsyncSession,
) -> Note:
    """Return the note or raise 404 (ownership enforced)."""
    result = await db.execute(
        select(Note).where(Note.id == note_id, Note.user_id == user_id)
    )
    note = result.scalars().first()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found",
        )
    return note


# ------------------------------------------------------------------ CRUD

@router.post("/", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Create a new note owned by the authenticated user."""
    note = Note(user_id=user_id, **note_data.model_dump())
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/", response_model=List[NoteOut])
async def list_notes(
    syllabus_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """List all notes owned by the authenticated user."""
    query = select(Note).where(Note.user_id == user_id).order_by(Note.id.desc())
    if syllabus_id is not None:
        query = query.where(Note.syllabus_id == syllabus_id)
    result = await db.execute(query)
    return result.scalars().all()


# ------------------------------------------------------------------ PDF Export

@router.get(
    "/{note_id}/pdf",
    response_class=Response,
    summary="Download note as PDF",
)
async def download_note_pdf(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Generate and download a formatted PDF of the note."""
    note = await _get_owned_note(note_id, user_id, db)

    syllabus_title = ""
    if note.syllabus_id:
        syllabus_result = await db.execute(select(Syllabus).where(Syllabus.id == note.syllabus_id))
        syllabus = syllabus_result.scalars().first()
        syllabus_title = syllabus.title if syllabus else ""

    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.colors import HexColor
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from io import BytesIO

    # Map the user's chosen font style to ReportLab built-in fonts.
    PDF_FONT_MAP = {
        "inter": "Helvetica",
        "jakarta": "Helvetica",
        "caveat": "Helvetica",
        "kalam": "Helvetica",
        "patrick": "Helvetica",
        "serif": "Times-Roman",
        "mono": "Courier",
    }
    body_font = PDF_FONT_MAP.get(note.font_style or "inter", "Helvetica")
    body_font_bold = body_font + "-Bold"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=HexColor("#6F4FB1"),
        spaceAfter=6,
        fontName=body_font_bold,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=11,
        textColor=HexColor("#64748B"),
        spaceAfter=4,
        fontName=body_font,
    )
    heading_style = ParagraphStyle(
        "CustomHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HexColor("#1E293B"),
        spaceBefore=16,
        spaceAfter=8,
        fontName=body_font_bold,
    )
    body_style = ParagraphStyle(
        "CustomBody",
        parent=styles["Normal"],
        fontSize=11,
        textColor=HexColor("#334155"),
        leading=14,
        spaceAfter=6,
        fontName=body_font,
    )
    bullet_style = ParagraphStyle(
        "Bullet",
        parent=body_style,
        leftIndent=24,
        bulletIndent=12,
        spaceAfter=4,
    )

    story = []

    # Header table
    header_data = [[
        Paragraph("Mentora", ParagraphStyle("Brand", parent=styles["Normal"], fontSize=20, textColor=HexColor("#6F4FB1"), fontName="Helvetica-Bold")),
        Paragraph("AI Academic Study Notes", ParagraphStyle("Tagline", parent=styles["Normal"], fontSize=10, textColor=HexColor("#64748B"), alignment=2)),
    ]]
    header_table = Table(header_data, colWidths=[4.5 * inch, 2.5 * inch])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 2, HexColor("#6F4FB1")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 12))

    # Title
    story.append(Paragraph(note.title, title_style))
    if syllabus_title:
        story.append(Paragraph(f"Syllabus: {syllabus_title}", ParagraphStyle("SyllabusTag", parent=styles["Normal"], fontSize=11, textColor=HexColor("#6F4FB1"), fontName="Helvetica-Bold", spaceAfter=16)))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    story.append(Spacer(1, 16))

    # AI Summary
    if note.ai_summary:
        story.append(Paragraph("★ AI Study Summary", heading_style))
        summary_box_style = ParagraphStyle(
            "SummaryBox",
            parent=body_style,
            backColor=HexColor("#EBE5F6"),
            borderColor=HexColor("#B6A3DE"),
            borderWidth=1,
            borderPadding=12,
            borderRadius=4,
        )
        # Use a table to create a boxed effect
        summary_data = [[Paragraph(strip_markdown(note.ai_summary), summary_box_style)]]
        summary_table = Table(summary_data, colWidths=[7 * inch])
        summary_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 1, HexColor("#B6A3DE")),
            ("BACKGROUND", (0, 0), (-1, -1), HexColor("#EBE5F6")),
            ("TOPPADDING", (0, 0), (-1, -1), 12),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ("LEFTPADDING", (0, 0), (-1, -1), 12),
            ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 16))

    # Note Content
    story.append(Paragraph("Note Content", heading_style))
    content_text = strip_markdown(note.content) if note.content else "No content."
    # Replace newlines with <br/> for Paragraph
    content_text = content_text.replace("\n", "<br/>")
    story.append(Paragraph(content_text, body_style))

    doc.build(story)
    buffer.seek(0)

    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{note.title.replace(" ", "_")}.pdf"'
        },
    )


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Retrieve a single note by id (must be owned by the authenticated user)."""
    return await _get_owned_note(note_id, user_id, db)


@router.put("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Update a note's title, content, syllabus linkage, or AI summary."""
    note = await _get_owned_note(note_id, user_id, db)
    update_dict = note_data.model_dump(exclude_unset=True)
    if "ai_summary" in update_dict and update_dict["ai_summary"] != note.ai_summary:
        note.summary_generated_at = datetime.now(timezone.utc)
    for field, value in update_dict.items():
        setattr(note, field, value)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Delete a note and its associated AI summary."""
    note = await _get_owned_note(note_id, user_id, db)
    await db.delete(note)
    await db.commit()
    return None


# ------------------------------------------------------------------ Syllabus Note Generation

@router.post(
    "/generate-from-syllabus",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
)
async def generate_note_from_syllabus(
    req: SyllabusNoteGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    quota: QuotaContext = Depends(require_ai_quota(UsageType.NOTE_GENERATION)),
):
    """Generate comprehensive study notes and an AI summary from an uploaded syllabus."""
    syllabus_result = await db.execute(
        select(Syllabus).where(Syllabus.id == req.syllabus_id, Syllabus.user_id == user_id)
    )
    syllabus = syllabus_result.scalars().first()
    if not syllabus:
        syllabus_result = await db.execute(
            select(Syllabus).where(Syllabus.id == req.syllabus_id)
        )
        syllabus = syllabus_result.scalars().first()

    if not syllabus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Syllabus not found",
        )

    from app.services.exam_service import ExamService
    content = ""
    if syllabus.parsed_data and isinstance(syllabus.parsed_data, dict):
        content = ExamService._build_content_from_parsed_data(syllabus.parsed_data)
    if not content and syllabus.extracted_text:
        content = syllabus.extracted_text[:10000]

    if not content or not content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Syllabus content is empty or unreadable.",
        )

    from app.services.llm_service import LLMService
    llm = LLMService()

    focus_instruction = f" Focus specifically on topic/unit: '{req.topic_focus}'." if req.topic_focus else ""

    notes_prompt = (
        "You are an expert academic tutor and note-taker. Given the following syllabus content, "
        "create comprehensive, clean, plain text study notes.\n\n"
        f"Syllabus Title: {syllabus.title or 'Syllabus Notes'}\n"
        f"{focus_instruction}\n\n"
        f"Syllabus Content:\n{content[:12000]}\n\n"
        "STRICT FORMATTING RULES:\n"
        "- Do NOT use any Markdown formatting syntax. Do NOT use **, *, ##, ###, #, _, `, or ```.\n"
        "- Use clean plain text formatting.\n"
        "- Use ALL-CAPS for main section headings.\n"
        "- Use '• ' for bullet points.\n"
        "- Organize notes unit-by-unit / chapter-by-chapter with clear explanations and core definitions.\n"
    )

    summary_prompt = (
        "Read the following syllabus content and generate a concise 3-5 bullet point AI study summary "
        "highlighting the top critical takeaways a student must remember.\n\n"
        f"Syllabus Title: {syllabus.title or 'Syllabus Summary'}\n"
        f"{focus_instruction}\n\n"
        f"Content:\n{content[:10000]}\n\n"
        "STRICT FORMATTING RULES:\n"
        "- Do NOT use any Markdown syntax (do NOT use **, *, #, `, etc).\n"
        "- Use bullet points starting with '• ' only.\n"
        "- Do not include introduction or closing text.\n"
    )

    try:
        raw_notes_text = await llm.generate(notes_prompt, temperature=0.3)
        notes_text = strip_markdown(raw_notes_text)
        raw_summary_text = await llm.generate(summary_prompt, temperature=0.3)
        summary_text = strip_markdown(raw_summary_text)
    except Exception as exc:
        logger.exception("AI note generation failed for syllabus %s: %s", req.syllabus_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate AI notes. Please try again.",
        ) from exc

    title_prefix = f"Notes: {req.topic_focus}" if req.topic_focus else f"Notes - {syllabus.title or 'Syllabus'}"
    note = Note(
        user_id=user_id,
        syllabus_id=req.syllabus_id,
        title=title_prefix[:255],
        content=notes_text,
        ai_summary=summary_text if summary_text else None,
        summary_generated_at=datetime.now(timezone.utc) if summary_text else None,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)

    await record_usage(db, user_id, UsageType.NOTE_GENERATION)
    return note


# ------------------------------------------------------------------ AI summary

@router.post(
    "/{note_id}/summary",
    response_model=NoteSummaryOut,
    status_code=status.HTTP_200_OK,
)
async def generate_summary(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    quota: QuotaContext = Depends(require_ai_quota(UsageType.NOTE_GENERATION)),
):
    """Generate (or regenerate) an AI summary for a note using the existing
    LLM service.  Ownership is enforced; the raw note content is sent to the
    LLM and the result is persisted back to the note row.
    """
    note = await _get_owned_note(note_id, user_id, db)

    if not note.content or not note.content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note content is empty. Add some content before generating a summary.",
        )

    # Reuse the existing LLM service — no second AI service is created.
    from app.services.llm_service import LLMService

    llm = LLMService()
    prompt = (
        "You are a study assistant. Read the following note and produce a concise, "
        "well-structured study summary in 3–5 bullet points. Focus on the key concepts, "
        "definitions, and important facts a student should remember.\n\n"
        f"Note title: {note.title}\n\n"
        f"Note content:\n{note.content.strip()}\n\n"
        "STRICT FORMATTING RULES:\n"
        "- Do NOT use any Markdown formatting syntax (do NOT use **, *, #, `, etc).\n"
        "- Use bullet points starting with '• ' only.\n"
        "- Respond with bullet points only."
    )

    try:
        raw_summary_text = await llm.generate(prompt, temperature=0.3)
        summary_text = strip_markdown(raw_summary_text)
        if not summary_text:
            raise ValueError("AI returned an empty summary.")
    except Exception as exc:
        logger.exception("AI summary generation failed for note %s: %s", note_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service is temporarily unavailable. Please try again.",
        ) from exc

    note.ai_summary = summary_text
    note.summary_generated_at = datetime.now(timezone.utc)
    db.add(note)
    await db.commit()
    await db.refresh(note)

    # Record quota usage only after success.
    await record_usage(db, user_id, UsageType.NOTE_GENERATION)

    return NoteSummaryOut(
        note_id=note.id,
        ai_summary=note.ai_summary,
        summary_generated_at=note.summary_generated_at,
    )


@router.delete("/{note_id}/summary", status_code=status.HTTP_204_NO_CONTENT)
async def delete_summary(
    note_id: int,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Clear the AI summary from a note without deleting the note itself."""
    note = await _get_owned_note(note_id, user_id, db)
    note.ai_summary = None
    note.summary_generated_at = None
    db.add(note)
    await db.commit()
    return None
