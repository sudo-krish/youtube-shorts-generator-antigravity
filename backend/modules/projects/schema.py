from pydantic import BaseModel, Field
from typing import Optional
import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class Project(BaseModel):
    __tablename__ = "projects"
    
    id: str = Field(default_factory=generate_uuid, json_schema_extra={"primary_key": True})
    user_id: str = Field(default="system")
    format: str = Field(description="LONG or SHORT")
    game_name: str
    game_genre: str
    theme: str
    created_at: str = Field(default_factory=lambda: datetime.datetime.utcnow().isoformat())
    status: str = Field(default="DRAFT")

class ScriptBlock(BaseModel):
    __tablename__ = "script_blocks"
    
    id: str = Field(default_factory=generate_uuid, json_schema_extra={"primary_key": True})
    project_id: str = Field(json_schema_extra={"index": True})
    block_index: int
    text_content: str
    estimated_duration_ms: Optional[int] = Field(default=0)
    status: str = Field(default="PENDING")
