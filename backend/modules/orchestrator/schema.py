from pydantic import BaseModel, Field
from typing import Optional

class Job(BaseModel):
    __tablename__ = "jobs"
    job_id: str = Field(json_schema_extra={"primary_key": True})
    video_id: str = Field(json_schema_extra={"index": True})
    status: str
    metadata: Optional[str] = "{}"
    num_chunks: int = 0
    created_at: float
    json_path: Optional[str] = None

class JobStage(BaseModel):
    __tablename__ = "job_stages"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    job_id: str = Field(json_schema_extra={"index": True})
    stage_name: str
    status: str
    logs: Optional[str] = None
    start_time: float
    end_time: Optional[float] = None
    chunk_id: Optional[int] = None
    model_id: Optional[int] = None

class JobRender(BaseModel):
    __tablename__ = "job_renders"
    id: str = Field(json_schema_extra={"primary_key": True})
    job_id: str = Field(json_schema_extra={"index": True})
    variant_id: str
    status: str
    error_logs: Optional[str] = ""
    outputs: Optional[str] = "[]"
    created_at: float
    updated_at: float
