import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from pydantic import BaseModel
from .schema import Project, ScriptBlock
from core.db.engine import get_session, engine

logger = logging.getLogger(__name__)

router = APIRouter()

class ProjectCreateRequest(BaseModel):
    format: str
    game_name: str
    game_genre: str
    theme: str

class ProjectResponse(BaseModel):
    project_id: str
    status: str

@router.post("/", response_model=ProjectResponse)
def create_project(req: ProjectCreateRequest, db: Session = Depends(get_session)):
    try:
        new_project = Project(
            format=req.format,
            game_name=req.game_name,
            game_genre=req.game_genre,
            theme=req.theme
        )
        # Using raw SQL via SQLAlchemy because we dynamically generated tables, 
        # or we can use standard inserts if we mapped them properly.
        # Given the registry dynamically creates sqlalchemy Table objects:
        from core.db.engine import generated_tables
        projects_table = generated_tables.get("projects")
        
        if projects_table is None:
            raise HTTPException(status_code=500, detail="Database table not initialized")
            
        stmt = projects_table.insert().values(**new_project.model_dump())
        db.execute(stmt)
        db.commit()
        
        return ProjectResponse(project_id=new_project.id, status="DRAFT")
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class FinalizeScriptRequest(BaseModel):
    project_id: str
    full_text: str

class FinalizeScriptResponse(BaseModel):
    blocks_created: int

@router.post("/script/finalize", response_model=FinalizeScriptResponse)
def finalize_script(req: FinalizeScriptRequest, db: Session = Depends(get_session)):
    try:
        paragraphs = [p.strip() for p in req.full_text.split("\n\n") if p.strip()]
        
        script_blocks_table = generated_tables.get("script_blocks")
        if script_blocks_table is None:
            from core.db.engine import generated_tables
            script_blocks_table = generated_tables.get("script_blocks")
            
        blocks_data = []
        for i, text_content in enumerate(paragraphs):
            # Heuristic: ~2.5 words per second
            word_count = len(text_content.split())
            estimated_seconds = word_count / 2.5
            duration_ms = int(estimated_seconds * 1000)
            
            block = ScriptBlock(
                project_id=req.project_id,
                block_index=i,
                text_content=text_content,
                estimated_duration_ms=duration_ms
            )
            blocks_data.append(block.model_dump())
            
        if blocks_data:
            stmt = script_blocks_table.insert().values(blocks_data)
            db.execute(stmt)
            
            # Update project status
            projects_table = generated_tables.get("projects")
            upd_stmt = projects_table.update().where(projects_table.c.id == req.project_id).values(status="MAPPED")
            db.execute(upd_stmt)
            
            db.commit()
            
        return FinalizeScriptResponse(blocks_created=len(blocks_data))
    except Exception as e:
        logger.error(f"Error finalizing script: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
