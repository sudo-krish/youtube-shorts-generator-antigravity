from pydantic import BaseModel
from typing import List, Dict, Any

class AgentResponse(BaseModel):
    output: str

class ObserverRequest(BaseModel):
    chunk_path: str
    metadata: Dict[str, Any]
    audio_spikes: List[Any]
    ocr_dumps: Dict[str, Any]
    semantic_matrix: Dict[str, Any]

class ScriptwriterRequest(BaseModel):
    context: str
    metadata: Dict[str, Any]
    web_trends: str

class DirectorRequest(BaseModel):
    context: str
    scripts: str
    metadata: Dict[str, Any]
    sfx_library: str
    music_library: str

class EditorRequest(BaseModel):
    scripts: str
    vision: str
    metadata: Dict[str, Any]
    yolo_tracking: List[Any]

class SpecialistRequest(BaseModel):
    breakdown: str
    metadata: Dict[str, Any]
    math_report: str
    youtube_rules: str
    capabilities: str

class BuilderRequest(BaseModel):
    validated_plans: str
    metadata: Dict[str, Any]
