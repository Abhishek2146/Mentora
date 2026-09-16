import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.database import get_db
from app.models.user import User
from app.models.syllabus import Syllabus
from app.models.note import Note
from app.models.mindmap import MindMap
from app.schemas.mindmap import MindMapCreate, MindMapResponse
from app.api.v1.auth import get_current_user
from app.ai.mindmap_generator.generator import generate_mindmap_data

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/generate", response_model=MindMapResponse)
async def generate_mindmap(
    request: MindMapCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate or regenerate a mind map for a given syllabus or note.
    """
    # 1. Fetch content
    text_content = ""
    title = "Generated Mind Map"
    
    if request.source_type == "syllabus":
        result = await db.execute(
            select(Syllabus).where(Syllabus.id == request.source_id, Syllabus.user_id == current_user.id)
        )
        syllabus = result.scalars().first()
        if not syllabus:
            raise HTTPException(status_code=404, detail="Syllabus not found")
        
        text_content = syllabus.extracted_text or syllabus.description or syllabus.title
        title = f"Mind Map: {syllabus.title}"
        
    elif request.source_type == "note":
        result = await db.execute(
            select(Note).where(Note.id == request.source_id, Note.user_id == current_user.id)
        )
        note = result.scalars().first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found")
            
        text_content = note.content or note.title
        title = f"Mind Map: {note.title}"
    else:
        raise HTTPException(status_code=400, detail="Invalid source_type. Must be 'syllabus' or 'note'.")

    if not text_content:
        raise HTTPException(status_code=400, detail="Source content is empty.")

    # 2. Check if a mind map already exists for this source
    result = await db.execute(
        select(MindMap).where(
            MindMap.source_type == request.source_type,
            MindMap.source_id == request.source_id,
            MindMap.user_id == current_user.id
        )
    )
    existing_mindmap = result.scalars().first()

    # 3. Generate from LLM
    try:
        generated_data = await generate_mindmap_data(text_content)
    except Exception as e:
        logger.error(f"Error generating mind map: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate mind map.")

    nodes = generated_data.get("nodes", [])
    edges = generated_data.get("edges", [])
    gen_title = generated_data.get("title", title)

    # 4. Save to DB
    if existing_mindmap:
        existing_mindmap.nodes = nodes
        existing_mindmap.edges = edges
        existing_mindmap.title = gen_title
        await db.commit()
        await db.refresh(existing_mindmap)
        return existing_mindmap
    else:
        new_mindmap = MindMap(
            user_id=current_user.id,
            source_type=request.source_type,
            source_id=request.source_id,
            title=gen_title,
            nodes=nodes,
            edges=edges,
        )
        db.add(new_mindmap)
        await db.commit()
        await db.refresh(new_mindmap)
        return new_mindmap

@router.get("/", response_model=List[MindMapResponse])
async def list_mindmaps(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all mind maps for the current user.
    """
    result = await db.execute(
        select(MindMap).where(MindMap.user_id == current_user.id).order_by(MindMap.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{mindmap_id}", response_model=MindMapResponse)
async def get_mindmap(
    mindmap_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific mind map by ID.
    """
    result = await db.execute(
        select(MindMap).where(MindMap.id == mindmap_id, MindMap.user_id == current_user.id)
    )
    mindmap = result.scalars().first()
    if not mindmap:
        raise HTTPException(status_code=404, detail="Mind map not found")
        
    return mindmap
