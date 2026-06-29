from pydantic import BaseModel, Field
from typing import Optional

class Video(BaseModel):
    __tablename__ = "videos"
    video_id: str = Field(json_schema_extra={"primary_key": True})
    video_name: str = Field(json_schema_extra={"unique": True})
    video_path: str
    created_at: float

class VideoChunk(BaseModel):
    __tablename__ = "video_chunks"
    chunk_id: str = Field(json_schema_extra={"primary_key": True})
    video_id: str = Field(json_schema_extra={"index": True})
    chunk_index: int
    chunk_name: str
    audio_chunk_name: Optional[str] = None
    start_time: float
    end_time: float

class TransformerTest(BaseModel):
    __tablename__ = "transformer_tests"
    test_id: str = Field(json_schema_extra={"primary_key": True})
    video_id: str = Field(json_schema_extra={"index": True})
    chunk_index: int
    transformer_name: str
    status: str
    start_time: float
    end_time: Optional[float] = None
    output_data: Optional[str] = None
    visual_output_path: Optional[str] = None
