from pydantic import BaseModel
from typing import Dict, Any

class CutterRequest(BaseModel):
    video_path: str
    timeline_json: Dict[str, Any]

class RenderRequest(BaseModel):
    clips_data: Dict[str, Any]
    output_path: str

class RenderTreeRequest(BaseModel):
    job_id: str
    chunk_index: int
    blueprint: Dict[str, Any]
    output_dir: str
