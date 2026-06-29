from pydantic import BaseModel, Field
from typing import Optional

class Model(BaseModel):
    __tablename__ = "models"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    provider: str
    model_name: str = Field(json_schema_extra={"unique": True})

class ModelUsage(BaseModel):
    __tablename__ = "model_usage"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    model_id: int = Field(json_schema_extra={"index": True})
    prompt_tokens: int
    completion_tokens: int
    cost: float
    timestamp: float

class RateLimit(BaseModel):
    __tablename__ = "rate_limits"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    model_id: int = Field(json_schema_extra={"index": True})
    timestamp: float
    error_message: str

class JobMemoryLog(BaseModel):
    __tablename__ = "job_memory_logs"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    job_id: str = Field(json_schema_extra={"index": True})
    start_time: float
    end_time: float
    description: str

class JobIngestionState(BaseModel):
    __tablename__ = "job_ingestion_state"
    id: Optional[int] = Field(default=None, json_schema_extra={"primary_key": True, "autoincrement": True})
    job_id: str = Field(json_schema_extra={"unique": True})
    last_processed_timestamp: float
